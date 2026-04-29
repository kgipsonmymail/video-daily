"""生成音色列表文档"""
import requests, os
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv('MINIMAX_API_KEY')
headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}

resp = requests.post('https://api.minimaxi.com/v1/get_voice', headers=headers, json={'voice_type': 'system'})
data = resp.json()

zh, en, jp, other = [], [], [], []
for v in data.get('system_voice', []):
    vid = v['voice_id']
    name = v.get('voice_name', '')
    desc = '；'.join(v.get('description', []))
    if 'Chinese' in vid or 'Cantonese' in vid:
        zh.append((vid, name, desc))
    elif 'English' in vid:
        en.append((vid, name, desc))
    elif 'Japanese' in vid:
        jp.append((vid, name, desc))
    else:
        other.append((vid, name, desc))

lines = []
lines.append('# MiniMax 系统音色列表\n')
lines.append('> 数据来源：POST /v1/get_voice，查询时间：2026-04-24\n')
lines.append(f'总计：{len(zh)} 中文 + {len(en)} 英文 + {len(jp)} 日文 + {len(other)} 其他语言 = {len(zh)+len(en)+len(jp)+len(other)} 个系统音色\n')

for group_name, group_data in [('中文音色', zh), ('英文音色', en), ('日文音色', jp), ('其他音色', other)]:
    lines.append(f'\n## {group_name}\n')
    lines.append('| voice_id | 名称 | 说明 |')
    lines.append('|----------|------|------|')
    for vid, name, desc in sorted(group_data, key=lambda x: x[0]):
        lines.append(f'| `{vid}` | {name} | {desc} |')

md_content = '\n'.join(lines)

out_path = r'C:\Users\Sunny\Documents\010工作台\program\claudecode\video-daily\ref\api\voice\音色列表.md'
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(md_content)

print(f'写入 {out_path}')
print(f'中文:{len(zh)} 英文:{len(en)} 日文:{len(jp)} 其他:{len(other)}')
