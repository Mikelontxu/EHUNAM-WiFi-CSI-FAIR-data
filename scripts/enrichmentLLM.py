import ollama


SYSTEM_PROMPT = """ Tu tarea es enriquecer los metadatos de archivos .mat con información adicional que puedas inferir a partir del nombre del archivo y de los metadatos ya extraídos.

"""


def call_ollama(prompt):
    try:
        response = ollama.chat(
            model="qwen2.5",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        return response.get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception as e:
        print(f"[!] Error al llamar a Ollama: {e}")
        return ""