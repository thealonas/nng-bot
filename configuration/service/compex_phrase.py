class ComplexPhrase:
    value: str

    def __init__(self, string: str):
        self.value = string

    def build(self, **kwargs) -> str:
        build_string = self.value
        for arg in kwargs.keys():
            build_string = build_string.replace("{" + arg + "}", str(kwargs[arg]))
        return build_string
