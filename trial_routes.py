"""Public first-lesson trial. Grading never creates accounts or learning progress."""
from flask import jsonify,render_template,request

def install_trial(app,legacy):
    def first():
        lessons=legacy['sorted_lessons']()
        return lessons[0] if lessons else None

    @app.get('/try-lesson')
    def trial_page():return render_template('trial.html')

    @app.get('/api/platform/trial')
    def trial_lesson():
        lesson=first()
        if not lesson:return jsonify(error='No trial lesson available'),404
        data={key:lesson.get(key,'') for key in ('id','title_lo','title_ko','description')}
        data['videos']=[legacy['public_video'](v,True,'student') for v in lesson.get('videos',[])]
        for section in ('homework','quiz','exam'):data[section]=legacy['public_questions'](lesson.get(section,[]))
        return jsonify(lesson=data,saved=False)

    @app.post('/api/platform/trial/grade')
    def trial_grade():
        d=request.get_json(silent=True)
        if not isinstance(d,dict) or set(d)!={'lesson','section','answers'} or d.get('section') not in ('quiz','exam') or not isinstance(d.get('answers'),dict):return jsonify(error='Invalid trial answers'),400
        lesson=first()
        if not lesson:return jsonify(error='No trial lesson available'),404
        if d['lesson']!=lesson['id']:return jsonify(error='Trial lesson changed; reload before checking'),409
        questions=lesson.get(d['section'],[]);by_id={q['id']:q for q in questions}
        if set(d['answers'])-set(by_id):return jsonify(error='Unexpected question'),400
        for qid,value in d['answers'].items():
            if type(value) is not int or not 0<=value<len(by_id[qid].get('options',[])):return jsonify(error='Invalid choice'),400
        score,detail=legacy['_grade'](questions,d['answers'])
        return jsonify(score=score,detail=detail,total=len(questions),saved=False)
