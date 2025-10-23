from transformers import MarianMTModel, MarianTokenizer
import torch

# Variabili globali per modello e tokenizer
model = None
tokenizer = None

def initialize_model(model_name="Helsinki-NLP/opus-mt-en-it"):
    """
    Inizializza e carica il modello e il tokenizer di traduzione.
    Questo dovrebbe essere chiamato una volta all'inizio dello script.
    """
    global model, tokenizer
    if model is None or tokenizer is None:
        print(f"Caricamento del modello '{model_name}' in corso... Questo potrebbe richiedere del tempo.")
        try:
            # Verifica se è disponibile una GPU
            device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"Utilizzo del dispositivo: {device}")

            tokenizer = MarianTokenizer.from_pretrained(model_name)
            model = MarianMTModel.from_pretrained(model_name).to(device)
            print("Modello caricato con successo.")
        except Exception as e:
            print(f"Errore durante il caricamento del modello: {e}")
            print("Assicurati di aver installato le dipendenze con 'pip install -r requirements.txt'")
            model = None
            tokenizer = None

def translate_local(text, source_lang, target_lang):
    """
    Traduci il testo usando un modello locale di Hugging Face.
    I parametri source_lang e target_lang sono presenti per compatibilità, 
    ma il modello caricato è specifico per una coppia di lingue.
    """
    global model, tokenizer

    if model is None or tokenizer is None:
        return "Errore: modello di traduzione locale non inizializzato."

    if not text.strip():
        return ""

    try:
        # Suddividi il testo in blocchi più piccoli (es. per paragrafi/linee)
        # per evitare di superare i limiti di input del modello.
        chunks = text.split('\n')
        translated_chunks = []

        for chunk in chunks:
            if chunk.strip():
                # Tokenizza il testo per il modello
                inputs = tokenizer(chunk, return_tensors="pt", padding=True, truncation=True, max_length=512).to(model.device)
                # Genera la traduzione
                translated_ids = model.generate(**inputs)
                # Decodifica il testo tradotto
                translated_text = tokenizer.decode(translated_ids[0], skip_special_tokens=True)
                translated_chunks.append(translated_text)

        return "\n".join(translated_chunks)

    except Exception as e:
        print(f"Errore durante la traduzione locale: {e}")
        return f"Errore di traduzione locale: {text}"