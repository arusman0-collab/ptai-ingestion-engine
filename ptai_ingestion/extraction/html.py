from pathlib import Path
from bs4 import BeautifulSoup
def extract_html(path: Path) -> tuple[str,dict]:
    soup=BeautifulSoup(path.read_bytes(),"html.parser")
    for node in soup(["script","style","nav","footer","aside","form","noscript"]): node.decompose()
    lines=[]
    for node in soup.find_all(["h1","h2","h3","h4","p","li","blockquote"]):
        value=node.get_text(" ",strip=True)
        if value: lines.append(value)
    return "\n\n".join(lines), {"method":"html_meaningful_elements"}