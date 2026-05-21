from commands import *
import os
import json

DEFAULT_SETTINGS = {
    "settings": {
        "neutralization": "SUBINDUSTRY",
        "decay": 10,
        "truncation": 0.1,
        "delay": 1,
        "universe": "TOP3000",
        "region": "USA"
    },
    "enable_sweep": True,
    "sweep_mode": "independent",
    "sweep_params": {}
}

def load_settings():
    if os.path.exists('settings.json'):
        try:
            with open('settings.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return DEFAULT_SETTINGS

_config = load_settings()
SETTINGS = _config.get("settings", DEFAULT_SETTINGS["settings"])
ENABLE_SWEEP = _config.get("enable_sweep", DEFAULT_SETTINGS["enable_sweep"])
SWEEP_MODE = _config.get("sweep_mode", DEFAULT_SETTINGS["sweep_mode"])
SWEEP_PARAMS = _config.get("sweep_params", DEFAULT_SETTINGS["sweep_params"])

# 讀取 alphas.txt 檔案中的公式
ALPHAS_FILE = 'alphas.txt'

def load_alphas_from_file():
    if not os.path.exists(ALPHAS_FILE):
        with open(ALPHAS_FILE, 'w', encoding='utf-8') as f:
            f.write("# 在此放入您的 Alpha 公式，支援多行書寫！\n")
            f.write("# 不同的公式之間請使用「---」來做區隔，讓公式內可自由包含空白行。\n")
            f.write("# 支援以 '#' 或 '//' 開頭的註解行。\n")
            f.write("open + close\n")
            f.write("---\n")
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
        if line_stripped == '---':
            # '---' 代表公式的區隔
            if current_lines:
                alphas.append(" ".join(current_lines))
                current_lines = []
        elif not line_stripped:
            # 忽略公式內的空白行，保持自由度
            continue
        elif line_stripped.startswith('#') or line_stripped.startswith('//'):
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
                        
        print(f"--- Parameter Sweep Enabled (Independent/One-Factor-at-a-Time) ---")
        print(f"Total simulations generated: {len(DATA)} (Duplicates filtered, Formulas: {len(codes)})")
        
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
        print(f"--- Parameter Sweep Enabled (Cartesian Product Grid Sweep) ---")
        print(f"Total simulations generated: {len(DATA)} (Formulas: {len(codes)} x Combinations: {len(DATA)//max(1, len(codes))})")
else:
    for code in codes:
        sim = SETTINGS.copy()
        sim['code'] = code
        DATA.append(sim)
    print(f"--- Single Parameter Mode Enabled ---")
    print(f"Total simulations generated: {len(DATA)}")

