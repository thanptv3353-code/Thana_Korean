"""Small authored starter dictionary; never replace existing entries."""
import os,sys,sqlite3
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
import app
with sqlite3.connect(os.environ.get('THANA_PLATFORM_DB',str(root/'data/platform.sqlite3'))) as c:
 for i,(ko,lo,category) in enumerate([('안녕하세요','ສະບາຍດີ','ທັກທາຍ / 인사'),('감사합니다','ຂອບໃຈ','ທັກທາຍ / 인사'),('학교','ໂຮງຮຽນ','ການສຶກສາ / 교육'),('회사','ບໍລິສັດ','ວຽກ / 직장'),('물','ນ້ຳ','ປະຈຳວັນ / 일상'),('책','ປຶ້ມ','ການສຶກສາ / 교육')]):
  c.execute('INSERT OR IGNORE INTO vocabulary VALUES (?,?,?,?,?,?,?,?,?)',('starter-word-'+str(i),ko,lo,category,'','','','',1))
print('Starter vocabulary added without replacing existing entries')
