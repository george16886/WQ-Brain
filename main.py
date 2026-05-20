import csv
import logging
import requests
import json
import time
import os
import pickle
from parameters import DATA
from concurrent.futures import ThreadPoolExecutor
from threading import current_thread

class WQSession(requests.Session):
    def __init__(self, json_fn='credentials.json'):
        super().__init__()
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Origin': 'https://platform.worldquantbrain.com',
            'Referer': 'https://platform.worldquantbrain.com/',
            'Sec-Ch-Ua': '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site'
        })
        for handler in logging.root.handlers:
            logging.root.removeHandler(handler)
        logging.basicConfig(encoding='utf-8', level=logging.INFO, format='%(asctime)s: %(message)s')
        self.json_fn = json_fn
        self.login()
        old_get, old_post = self.get, self.post
        def new_get(*args, **kwargs):
            for i in range(5):
                try:
                    return old_get(*args, **kwargs)
                except Exception as e:
                    logging.info(f"new_get Exception (retry {i+1}/5): {e}")
                    time.sleep(2)
            return old_get(*args, **kwargs)
        def new_post(*args, **kwargs):
            for i in range(5):
                try:
                    return old_post(*args, **kwargs)
                except Exception as e:
                    logging.info(f"new_post Exception (retry {i+1}/5): {e}")
                    time.sleep(2)
            return old_post(*args, **kwargs)
        self.get, self.post = new_get, new_post
        self.login_expired = False
        self.rows_processed = []

    def login(self):
        if os.path.exists('cookies.pkl'):
            with open('cookies.pkl', 'rb') as f:
                self.cookies.update(pickle.load(f))
            r = self.get('https://api.worldquantbrain.com/authentication')
            if r.status_code == 200 and 'user' in r.json():
                logging.info('Logged in to WQBrain using saved cookies!')
                return
            else:
                logging.info('Saved cookies expired or invalid. Logging in again...')
                self.cookies.clear()

        if os.path.exists(self.json_fn):
            with open(self.json_fn, 'r') as f:
                creds = json.loads(f.read())
                email, password = creds['email'], creds['password']
        else:
            import getpass
            print(f"{self.json_fn} not found. Please enter your WorldQuant Brain credentials.")
            email = input("Email: ")
            password = getpass.getpass("Password: ")
            with open(self.json_fn, 'w') as f:
                json.dump({'email': email, 'password': password}, f, indent=4)
                
        self.auth = (email, password)
        r = self.post('https://api.worldquantbrain.com/authentication')
        if 'user' not in r.json():
            if 'inquiry' in r.json():
                print(f"Please complete biometric authentication at {r.url}/persona?inquiry={r.json()['inquiry']} before continuing...")
                print("Waiting 60 seconds for you to verify...")
                time.sleep(60)
                self.post(f"{r.url}/persona", json=r.json())
            else:
                print(f'WARNING! {r.json()}')
                time.sleep(10)
                
        with open('cookies.pkl', 'wb') as f:
            pickle.dump(self.cookies, f)
        logging.info('Logged in to WQBrain and saved cookies!')

    def simulate(self, data):
        self.rows_processed = []

        def process_simulation(writer, f, simulation):
            if self.login_expired: return # expired crendentials

            thread = current_thread().name
            alpha = simulation['code'].strip()
            delay = simulation.get('delay', 1)
            universe = simulation.get('universe', 'TOP3000')
            truncation = simulation.get('truncation', 0.1)
            region = simulation.get('region', 'USA')
            decay = simulation.get('decay', 6)
            neutralization = simulation.get('neutralization', 'SUBINDUSTRY').upper()
            pasteurization = simulation.get('pasteurization', 'ON')
            nan = simulation.get('nanHandling', 'OFF')
            logging.info(f"{thread} -- Simulating alpha: {alpha}")
            ok = True
            nxt = ""
            while True:
                # keep sending a post request until the simulation link is found
                try:
                    r = self.post('https://api.worldquantbrain.com/simulations', json={
                        'regular': alpha,
                        'type': 'REGULAR',
                        'settings': {
                            "nanHandling":nan,
                            "instrumentType":"EQUITY",
                            "delay":delay,
                            "universe":universe,
                            "truncation":truncation,
                            "unitHandling":"VERIFY",
                            "pasteurization":pasteurization,
                            "region":region,
                            "language":"FASTEXPR",
                            "decay":decay,
                            "neutralization":neutralization,
                            "visualization":False
                        }
                    })
                    if getattr(r, 'status_code', 200) >= 400:
                        try:
                            if 'credentials' in r.json().get('detail', ''):
                                self.login_expired = True
                                return
                        except Exception:
                            pass
                        
                        if getattr(r, 'status_code', 200) < 500:
                            ok = (False, getattr(r, 'content', 'Bad Request'))
                            break
                            
                        logging.info(f'{thread} -- Error {r.status_code}: {r.content}')
                        return
                    
                    nxt = r.headers['Location']
                    break
                except Exception as e:
                    logging.info(f'{thread} -- Exception: {e}')
                    return
            
            if ok == True:
                logging.info(f'{thread} -- Obtained simulation link: {nxt}')
                while True:
                    try:
                        resp = self.get(nxt)
                        r = resp.json()
                    except Exception as e:
                        logging.info(f"{thread} -- Error fetching or parsing simulation status: {e}. Retrying in 10s...")
                        time.sleep(10)
                        continue
                    
                    if 'alpha' in r:
                        alpha_link = r['alpha']
                        break
                    
                    try:
                        logging.info(f"{thread} -- Waiting for simulation to end ({int(100*r['progress'])}%)")
                    except Exception as e:
                        ok = (False, r.get('message', r.get('error', str(e))))
                        break
                    time.sleep(10)
                    
            if ok != True:
                logging.info(f'{thread} -- Issue when sending simulation request: {ok[1]}')
                row = [
                    0, delay, region,
                    neutralization, decay, truncation,
                    0, 0, 0, 'FAIL', 0, -1, universe, nxt, alpha
                ]
            else:
                r = self.get(f'https://api.worldquantbrain.com/alphas/{alpha_link}').json()
                logging.info(f'{thread} -- Obtained alpha link: https://platform.worldquantbrain.com/alpha/{alpha_link}')
                passed = 0
                for check in r['is']['checks']:
                    passed += check['result'] == 'PASS'
                    if check['name'] == 'CONCENTRATED_WEIGHT':
                        weight_check = check['result']
                    if check['name'] == 'LOW_SUB_UNIVERSE_SHARPE':
                        subsharpe = check['value']
                try:    subsharpe
                except: subsharpe = -1
                row = [
                    passed, delay, region,
                    neutralization, decay, truncation,
                    r['is']['sharpe'],
                    r['is']['fitness'],
                    round(100*r['is']['turnover'], 2),
                    weight_check, subsharpe, -1,
                    universe, f'https://platform.worldquantbrain.com/alpha/{alpha_link}', alpha
                ]
            writer.writerow(row)
            f.flush()
            self.rows_processed.append(simulation)
            logging.info(f'{thread} -- Result added to CSV!')

        try:
            for handler in logging.root.handlers:
                logging.root.removeHandler(handler)
            csv_file = f"data/api_{str(time.time()).replace('.', '_')}.csv"
            self.csv_file = csv_file
            log_file = csv_file.replace('csv', 'log')
            
            # Configure logging to write to both the log file and console stream
            formatter = logging.Formatter('%(asctime)s: %(message)s')
            
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(formatter)
            file_handler.setLevel(logging.INFO)
            
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            console_handler.setLevel(logging.INFO)
            
            logging.root.setLevel(logging.INFO)
            logging.root.addHandler(file_handler)
            logging.root.addHandler(console_handler)
            
            logging.info(f'Creating CSV file: {csv_file}')
            with open(csv_file, 'w', newline='') as f:
                writer = csv.writer(f)
                header = [
                    'passed', 'delay', 'region', 'neutralization', 'decay', 'truncation',
                    'sharpe', 'fitness', 'turnover', 'weight',
                    'subsharpe', 'correlation', 'universe', 'link', 'code'
                ]
                writer.writerow(header)
                with ThreadPoolExecutor(max_workers=3) as executor: # Reduced to 3 to avoid triggering WQBrain bot protection (session expiry)
                    list(executor.map(lambda sim: (time.sleep(1), process_simulation(writer, f, sim))[1], data))
        except Exception as e:
            print(f'Issue occurred! {type(e).__name__}: {e}')
        return [sim for sim in data if sim not in self.rows_processed]

if __name__ == '__main__':
    TOTAL_ROWS = len(DATA)
    wq = None
    while DATA:
        if wq is None or wq.login_expired:
            wq = WQSession()
        print(f'{TOTAL_ROWS-len(DATA)}/{TOTAL_ROWS} alpha simulations...')
        DATA = wq.simulate(DATA)

    # Show results
    if wq and hasattr(wq, 'csv_file') and os.path.exists(wq.csv_file):
        print("\n" + "="*80)
        print(" SIMULATION RESULTS ".center(80, "="))
        print("="*80)
        with open(wq.csv_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
            if len(rows) > 1:
                headers = rows[0]
                key_cols = ['passed', 'region', 'neutralization', 'decay', 'sharpe', 'fitness', 'turnover', 'weight', 'code']
                col_indices = []
                for col in key_cols:
                    if col in headers:
                        col_indices.append((col, headers.index(col)))
                
                col_widths = {}
                for col_name, idx in col_indices:
                    col_widths[col_name] = len(col_name)
                    for row in rows[1:]:
                        if idx < len(row):
                            col_widths[col_name] = max(col_widths[col_name], len(str(row[idx])))
                
                header_line = " | ".join(col_name.upper().ljust(col_widths[col_name]) for col_name, _ in col_indices)
                print(header_line)
                print("-" * len(header_line))
                
                for row in rows[1:]:
                    row_line = " | ".join(str(row[idx]).ljust(col_widths[col_name]) for col_name, idx in col_indices)
                    print(row_line)
            else:
                print("No results recorded.")
        print("="*80)
        print(f"Full results saved to: {os.path.abspath(wq.csv_file)}")
        print("="*80)
