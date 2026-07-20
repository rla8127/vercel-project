try:
    from evaluate import EvaluationHandler
except ImportError:
    from .evaluate import EvaluationHandler


class handler(EvaluationHandler):
    pass
