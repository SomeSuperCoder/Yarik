import re, russtress
accent = russtress.Accent()
input_text = "Проставь, пожалуйста, ударения"
accented_text = accent.put_stress(input_text)
output_text = re.compile(r"(.)\'", re.UNICODE).sub(r"+\1", accented_text)
print(output_text)  # "Прост+авь, пож+алуйста, удар+ения"