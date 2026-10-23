# Track JSONModel (Local Models)

Mostra na barra de estado (canto inferior direito) os JSONModels usados num controller SAPUI5, separados entre **leitura** (`getModel`) e **definição** (`setModel`).

![Barra de estado com os modelos](images/01-barra.gif)

## Funcionalidades

- Lista os modelos lidos com `getModel` (⬇) e os definidos com `setModel` (⬆)
- Tooltip com as linhas onde cada modelo aparece
- Clique na barra para abrir a lista e saltar para a linha
- Ignora linhas comentadas

## Como usar

1. Abre um ficheiro `*.controller.js` ou `*.controller.ts`.
2. Olha para a barra de estado, no canto inferior direito.
3. Passa o rato sobre a barra para ver as linhas de cada modelo.
4. Clica na barra (ou usa `Ctrl+Shift+P` → **JSON Models: mostrar lista**) e escolhe um item.

![Tooltip com as linhas](images/02-tooltip.gif)

![Lista de modelos](images/03-lista.gif)

## Exemplo

```javascript
this.getModel('BoardColumns');              // ⬇ leitura
this.getView().setModel(oModel, 'Tasks');   // ⬆ definição
```

Resultado na barra: `⬇ BoardColumns | ⬆ Tasks`

## Resolução de problemas

| Sintoma | Causa provável | Solução |
|---|---|---|
| Não aparece nada | O ficheiro não termina em `.controller.js` / `.controller.ts` | Abre o controller correto |
| "sem JSONModels" | Não há `getModel`/`setModel` com nome literal | Confirma que o nome está entre aspas |
| Não atualiza | Atraso ou versão antiga | Grava (`Ctrl+S`) ou usa **Developer: Reload Window** |

## Limitações

- Só reconhece nomes escritos diretamente como texto (`'BoardColumns'`). Nomes vindos de variáveis não aparecem.
- Só funciona em `*.controller.js` e `*.controller.ts`.
- Baseia-se em expressões regulares, por isso pode falhar em código fora do padrão habitual.

## Instalação

Descarrega o `.vsix`. Em Extensões (`Ctrl+Shift+X`), clica em **⋯ → Install from VSIX**.