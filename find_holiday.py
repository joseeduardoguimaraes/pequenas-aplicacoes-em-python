import tkinter as tk
from tkinter import filedialog, messagebox
import PyPDF2
import requests
import re
from datetime import datetime
from collections import defaultdict


PADRAO_DATA = re.compile(
    r"\b(?:\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})\b"
)

def extrair_texto_pdf(caminho_pdf):
    """Tenta extrair texto com PyPDF2; faz fallback entre métodos e evita Nones."""
    texto = ""
    try:
        with open(caminho_pdf, "rb") as f:
            leitor = PyPDF2.PdfReader(f)
            for pagina in leitor.pages:
                
                try:
                    conteudo = pagina.extract_text()
                except Exception:
                    try:
                        conteudo = pagina.extractText()
                    except Exception:
                        conteudo = None
                if conteudo:
                    texto += conteudo + "\n"
    except Exception as e:
        
        raise RuntimeError(f"Erro ao ler o PDF: {e}")
    return texto

def encontrar_datas_no_texto(texto):
    """Retorna lista de strings de datas encontradas pelo regex."""
    return PADRAO_DATA.findall(texto)

def normalizar_data_para_api(data_str):
    """
    Recebe uma string de data em vários formatos e retorna (yyyy-mm-dd).
    Retorna None se não conseguir parsear.
    """
    formatos = [
        "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d",
        "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
        "%d/%m/%y", "%d-%m-%y", "%d.%m.%y"
    ]
    for fmt in formatos:
        try:
            dt = datetime.strptime(data_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None

def verificar_feriados_por_datas(lista_datas):
    """
    Recebe lista de strings de data (qualquer formato reconhecido),
    consulta a API por ano e retorna dicionário {original_string: True/False}
    """
    resultado = {}
    anos_para_consultar = set()
    mapeadas = {}  

    
    for s in lista_datas:
        norm = normalizar_data_para_api(s)
        mapeadas[s] = norm
        if norm:
            anos_para_consultar.add(norm.split("-")[0])

    
    feriados_por_ano = {}
    for ano in anos_para_consultar:
        try:
            url = f"https://date.nager.at/api/v3/PublicHolidays/{ano}/BR"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                lista = resp.json()
                
                feriados_por_ano[ano] = {item.get("date") for item in lista if item.get("date")}
            else:
                
                feriados_por_ano[ano] = set()
        except Exception:
            feriados_por_ano[ano] = set()

   
    for original, norm in mapeadas.items():
        if not norm:
            resultado[original] = False  
        else:
            ano = norm.split("-")[0]
            is_feriado = norm in feriados_por_ano.get(ano, set())
            resultado[original] = bool(is_feriado)

    return resultado


def escolher_arquivo():
    caminho = filedialog.askopenfilename(
        title="Selecione um arquivo PDF",
        filetypes=[("Arquivos PDF", "*.pdf")]
    )
    if not caminho:
        return

    try:
        texto = extrair_texto_pdf(caminho)
    except RuntimeError as e:
        messagebox.showerror("Erro", str(e))
        return

    datas_encontradas = encontrar_datas_no_texto(texto)
    if not datas_encontradas:
        messagebox.showinfo("Resultado", "Nenhuma data detectada no PDF.")
        resultado_texto.delete(1.0, tk.END)
        resultado_texto.insert(tk.END, "Nenhuma data detectada no PDF.")
        return

    verif = verificar_feriados_por_datas(datas_encontradas)

    
    resultado_texto.delete(1.0, tk.END)
    resultado_texto.insert(tk.END, f"Datas encontradas ({len(datas_encontradas)}):\n\n")
    for d in datas_encontradas:
        status = "FERIADO" if verif.get(d) else "Não é feriado"
        resultado_texto.insert(tk.END, f"{d}  ->  {status}\n")


janela = tk.Tk()
janela.title("Verificador de Feriados (robusto)")

btn_escolher = tk.Button(janela, text="Escolher arquivo PDF", command=escolher_arquivo)
btn_escolher.pack(pady=10)

resultado_texto = tk.Text(janela, width=60, height=20)
resultado_texto.pack(pady=10)

janela.mainloop()
