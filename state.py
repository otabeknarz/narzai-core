import redis


class RedisMR:
    """
    12345: 
    {
        "state": "askFromUser",
        "first_description": str,
        "summary": str,
        "tz": str,
        "questions_answers": list[tuple[str, str]],
    }
    """
    def __init__(self) -> None:
        self.client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

    def set_state(self, id: str, state: str) -> bool:
        return True
