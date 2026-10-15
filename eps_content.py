"""Shared EPS payload rules: explanations are revealed only after grading."""
DIFFICULTIES = ('beginner', 'intermediate', 'advanced')


def public_question(question):
    return {k: v for k, v in question.items() if k not in ('answer', 'source', 'explanation_ko', 'explanation_lo')}


def explanations(question):
    return {key: question.get(key, '') for key in ('explanation_ko', 'explanation_lo')}
