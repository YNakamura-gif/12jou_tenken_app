import os

# データの内容
content = '''場所,劣化名
1階廊下,ひび割れ
2階廊下,剥離
屋上,漏水
外壁,腐食
階段,変形
玄関,欠損
機械室,さび
駐車場,変色'''

# dataディレクトリが存在しない場合は作成
if not os.path.exists('data'):
    os.makedirs('data')

# ファイルをShift-JISで保存
with open('data/master_data.csv', 'w', encoding='shift_jis') as f:
    f.write(content) 