"""Resolve shared lesson words from current public vocabulary, never draft text."""
def public_word(c,wid):
    row=c.execute('SELECT id,ko,lo,category,example_ko,example_lo,audio_ko,audio_lo FROM vocabulary WHERE id=? AND published=1',(wid,)).fetchone()
    if not row:return None
    word=dict(row)
    details=c.execute('SELECT part_of_speech,image_url FROM vocabulary_details WHERE word=?',(wid,)).fetchone()
    word.update(dict(details) if details else {'part_of_speech':'','image_url':''})
    if word['image_url']:
        asset=c.execute('SELECT published FROM media_assets WHERE filename=? AND kind=?',(word['image_url'].split('/')[-1],'image')).fetchone()
        if not asset or not asset['published']:word['image_url']=''
    return word
