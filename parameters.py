from commands import *
import os

# 預設模擬設定模板
SETTINGS = {
    'neutralization': 'SUBINDUSTRY',
    'decay': 10,
    'truncation': 0.1,
    'delay': 1,
    'universe': 'TOP3000',
    'region': 'USA'
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
for code in codes:
    sim = SETTINGS.copy()
    sim['code'] = code
    DATA.append(sim)

