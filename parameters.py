from commands import *
import os

# 預設模擬設定模板 (非掃描模式下使用)
SETTINGS = {
    'neutralization': 'SUBINDUSTRY',
    'decay': 10,
    'truncation': 0.1,
    'delay': 1,
    'universe': 'TOP3000',
    'region': 'USA'
}

# ==================== 參數掃描設定 (Parameter Sweep Settings) ====================
# 設為 True 即可啟用多參數掃描；設為 False 則使用上方單一的 SETTINGS
ENABLE_SWEEP = True

# 選擇掃描模式：
# 'independent': 獨立單一參數掃描 (每次只變動一個參數，其餘保持預設，避免組合爆炸)
# 'grid': 笛卡爾積交叉掃描 (測試所有可能的排列組合)
SWEEP_MODE = 'independent'

SWEEP_PARAMS = {
    'universe': ['TOP3000', 'TOP2000', 'TOP1000', 'TOP500', 'TOP200', 'TOPSP500'],
    'delay': [1, 0],
    'neutralization': ['NONE', 'MARKET', 'SECTOR', 'INDUSTRY', 'SUBINDUSTRY'],
    'decay': [0, 1, 5, 10, 15],
    'truncation': [0.01, 0.05, 0.1]
}

# 讀取 alphas.txt 檔案中的公式
ALPHAS_FILE = 'alphas.txt'

def load_alphas_from_file():
    if not os.path.exists(ALPHAS_FILE):
        with open(ALPHAS_FILE, 'w', encoding='utf-8') as f:
            f.write("# 在此放入您的 Alpha 公式，支援多行書寫！\n")
            f.write("# 不同的公式之間請使用「空白行（Double Newline）」來做區隔。\n")
            f.write("# 支援以 '#' 開頭的註解行。\n")
            f.write("open + close\n\n")
            f.write("# 這是一個多行公式的範例：\n")
            f.write("rank(\n")
            f.write("    ts_sum(close - open, 10) /\n")
            f.write("    ts_sum(high - low, 10)\n")
            f.write(")\n")
            
    alphas = []
    with open(ALPHAS_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
        
    current_lines = []
    for line in content.splitlines():
        line_stripped = line.strip()
        if not line_stripped:
            # 空白行代表公式的區隔
            if current_lines:
                alphas.append(" ".join(current_lines))
                current_lines = []
        elif line_stripped.startswith('#'):
            # 註解行忽略
            continue
        else:
            current_lines.append(line_stripped)
            
    if current_lines:
        alphas.append(" ".join(current_lines))
        
    return alphas


# === 選擇您的公式來源 ===
# 來源 1: 從 alphas.txt 讀取 (預設)
codes = load_alphas_from_file()

# 來源 2: 從 commands.py 中自動生成 (取消註解即可切換)
# codes = from_arxiv()  # 101 Alphas
# codes = scale_and_corr()  # 組合排列公式

# 自動組合設定與公式生成 DATA
DATA = []
if ENABLE_SWEEP:
    if SWEEP_MODE == 'independent':
        # 獨立參數掃描 (One-Factor-at-a-Time)
        generated_keys = set()
        for code in codes:
            # 1. 先加入一組完全使用預設 SETTINGS 的基準任務
            base_sim = SETTINGS.copy()
            base_sim['code'] = code
            base_key = (code, tuple(sorted((k, v) for k, v in SETTINGS.items() if k != 'code')))
            DATA.append(base_sim)
            generated_keys.add(base_key)
            
            # 2. 針對每個變數獨立進行掃描，其他欄位維持預設
            for param_name, values in SWEEP_PARAMS.items():
                for val in values:
                    sim = SETTINGS.copy()
                    sim[param_name] = val
                    sim['code'] = code
                    
                    # 避免生成重複的基準任務組合
                    sim_key = (code, tuple(sorted((k, v) for k, v in sim.items() if k != 'code')))
                    if sim_key not in generated_keys:
                        DATA.append(sim)
                        generated_keys.add(sim_key)
                        
        print(f"--- 參數掃描模式已啟用 (獨立單一變數掃描模式) ---")
        print(f"共生成 {len(DATA)} 組模擬任務 (已過濾重複項，公式數: {len(codes)})")
        
    elif SWEEP_MODE == 'grid':
        # 笛卡爾積交叉掃描 (Cartesian Product Grid Sweep)
        import itertools
        keys, values = zip(*SWEEP_PARAMS.items())
        for code in codes:
            for combination in itertools.product(*values):
                sim = SETTINGS.copy()
                sim.update(dict(zip(keys, combination)))
                sim['code'] = code
                DATA.append(sim)
        print(f"--- 參數掃描模式已啟用 (笛卡爾積交叉掃描模式) ---")
        print(f"共生成 {len(DATA)} 組模擬任務 (公式數: {len(codes)} x 參數組合數: {len(DATA)//max(1, len(codes))})")
else:
    for code in codes:
        sim = SETTINGS.copy()
        sim['code'] = code
        DATA.append(sim)
    print(f"--- 單一參數模式已啟用 ---")
    print(f"共生成 {len(DATA)} 組模擬任務")

