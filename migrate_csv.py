
import csv

input_file = 'data.csv'
output_file = 'data_new.csv'

def get_difficulty_text(score):
    score = int(score)
    if score <= 30:
        return '简单'
    elif score <= 60:
        return '中等'
    else:
        return '困难'

with open(input_file, 'r', encoding='utf-8-sig') as f_in, \
     open(output_file, 'w', encoding='utf-8-sig', newline='') as f_out:
    
    # data.csv is space separated, not comma
    for line in f_in:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 6:
            # 120.285 31.025 100 0 150 山腰观测点1
            # difficulty is at index 2
            diff_score = parts[2]
            diff_text = get_difficulty_text(diff_score)
            parts[2] = diff_text
            f_out.write(' '.join(parts) + '\n')

print("Conversion complete.")
