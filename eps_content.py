"""Shared EPS payload rules: explanations are revealed only after grading."""
DIFFICULTIES = ('beginner', 'intermediate', 'advanced')


def public_question(question):
    return {**{k: v for k, v in question.items() if k not in ('answer', 'source', 'explanation_ko', 'explanation_lo')}, 'skill': question_skill(question)}


def explanations(question):
    return {key: question.get(key, '') for key in ('explanation_ko', 'explanation_lo')}

SKILLS = ('reading', 'listening')


def question_skill(question):
    return question.get('skill', 'reading')


def available_questions(connection, questions, skill):
    """Listening runs can use only published library audio, never draft assets."""
    rows=connection.execute("SELECT m.filename,g.asset AS generated FROM media_assets m LEFT JOIN generated_audio g ON g.asset=m.id WHERE m.kind='audio' AND m.published=1").fetchall()
    audio={'/media/library/'+row['filename'] for row in rows}
    generated={'/media/library/'+row['filename'] for row in rows if row['generated']}
    matching=[q for q in questions if question_skill(q)==skill]
    unavailable_groups={q.get('source','').split('-')[0] for q in matching if skill=='listening' and q['category']=='reading' and q.get('audio') not in audio}
    return [{**q,'audio_ai_generated':q.get('audio') in generated} if skill=='listening' else q for q in matching if (skill!='listening' or q.get('audio') in audio) and not (q['category']=='reading' and q.get('source','').split('-')[0] in unavailable_groups)]
