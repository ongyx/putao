import cattrs

converter = cattrs.Converter(omit_if_default=True)
converter.register_unstructure_hook(int, str)
converter.register_unstructure_hook(float, lambda f: f"{f:0.2f}")
converter.register_unstructure_hook(bool, lambda b: "true" if b else "false")
