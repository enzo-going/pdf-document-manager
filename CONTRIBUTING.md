# Contribuindo

Pull requests são bem-vindos. Para mudanças grandes, abra uma issue antes para
discutir o que você pretende alterar.

Antes de abrir o PR, rode no `backend/` o mesmo que o CI roda:

```bash
cd backend
pip install -r requirements.txt
ruff check .
pytest -q
```

O `ruff.toml` liga só as regras que apontam erro de verdade (`F` e `E9`); estilo
fica de fora de propósito. O `frontend/` é HTML, CSS e JavaScript sem etapa de
build: para testar a interface, suba a API (`python run.py`) e abra
`frontend/index.html`, como descrito no README.
