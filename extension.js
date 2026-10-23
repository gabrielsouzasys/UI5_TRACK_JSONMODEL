const vscode = require ('vscode');

let statusItem;
let models = []; 
let debounceTimer;

const isController = doc => /\.controller\.(js|ts)$/.test (doc.uri.path);

function activate (context) {
  statusItem = vscode.window.createStatusBarItem (
    vscode.StatusBarAlignment.Right,
    100
  );
  statusItem.command = 'jsonModels.show';

  context.subscriptions.push (
    statusItem,
    vscode.commands.registerCommand ('jsonModels.show', showPicker),
    vscode.window.onDidChangeActiveTextEditor (scheduleUpdate),
    vscode.workspace.onDidChangeTextDocument (e => {
      const ed = vscode.window.activeTextEditor;
      if (ed && e.document === ed.document) scheduleUpdate ();
    }),
    vscode.workspace.onDidSaveTextDocument (scheduleUpdate)
  );

  update ();
}

function scheduleUpdate () {
  clearTimeout (debounceTimer);
  debounceTimer = setTimeout (update, 300);
}

function update () {
  const editor = vscode.window.activeTextEditor;
  if (!editor || !isController (editor.document)) {
    statusItem.hide ();
    return;
  }

  models = parse (editor.document.getText ());

  const gets = models.filter (m => m.gets.length).map (m => m.name);
  const sets = models.filter (m => m.sets.length).map (m => m.name);

  const parts = [];
  if (gets.length) parts.push (`$(arrow-down) ${gets.join (', ')}`);
  if (sets.length) parts.push (`$(arrow-up) ${sets.join (', ')}`);
  statusItem.text = parts.length
    ? parts.join ('   |   ')
    : '$(database) sem JSONModels';

  const md = new vscode.MarkdownString ();
  for (const m of models) {
    md.appendMarkdown (`**${m.name}**\n\n`);
    if (m.gets.length)
      md.appendMarkdown (`- getModel: linhas ${m.gets.join (', ')}\n`);
    if (m.sets.length)
      md.appendMarkdown (`- setModel: linhas ${m.sets.join (', ')}\n`);
    md.appendMarkdown ('\n');
  }
  statusItem.tooltip = md;
  statusItem.show ();
}

function parse (raw) {
  // troca comentários por espaços
  const code = raw.replace (/\/\*[\s\S]*?\*\/|\/\/[^\n]*/g, m =>
    m.replace (/[^\n]/g, ' ')
  );
  const map = new Map ();

  const add = (name, kind, index) => {
    if (!map.has (name)) map.set (name, {name, gets: [], sets: []});
    const line = code.slice (0, index).split ('\n').length;
    const list = map.get (name)[kind];
    if (!list.includes (line)) list.push (line);
  };

  // .getModel('X')  ou  .getModel ('X')
  for (const m of code.matchAll (/\.getModel\s*\(\s*['"]([^'"]+)['"]\s*\)/g)) {
    add (m[1], 'gets', m.index);
  }
  // .setModel(qualquer_coisa, 'X')
  for (const m of code.matchAll (
    /\.setModel\s*\([^;]*?,\s*['"]([^'"]+)['"]\s*\)/g
  )) {
    add (m[1], 'sets', m.index);
  }

  return [...map.values ()].sort ((a, b) => a.name.localeCompare (b.name));
}

async function showPicker () {
  const editor = vscode.window.activeTextEditor;
  if (!editor || !isController (editor.document) || !models.length) {
    vscode.window.showInformationMessage ('Nenhum JSONModel neste controller.');
    return;
  }

  const items = models
    .flatMap (m => [
      ...m.sets.map (line => ({
        label: `$(arrow-up) ${m.name}`,
        description: `setModel · linha ${line}`,
        line,
      })),
      ...m.gets.map (line => ({
        label: `$(arrow-down) ${m.name}`,
        description: `getModel · linha ${line}`,
        line,
      })),
    ])
    .sort ((a, b) => a.line - b.line);

  const pick = await vscode.window.showQuickPick (items, {
    placeHolder: 'JSONModels deste controller (Enter para ir à linha)',
  });
  if (!pick) return;

  const pos = new vscode.Position (pick.line - 1, 0);
  editor.selection = new vscode.Selection (pos, pos);
  editor.revealRange (
    new vscode.Range (pos, pos),
    vscode.TextEditorRevealType.InCenter
  );
}

function deactivate () {}

module.exports = {activate, deactivate};
