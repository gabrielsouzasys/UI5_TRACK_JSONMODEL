import math
import os
import re

from PIL import Image, ImageDraw, ImageFont

OUT = "/mnt/user-data/outputs/images"
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- fontes
FD = "/usr/share/fonts/truetype/dejavu/"
UI       = ImageFont.truetype(FD + "DejaVuSans.ttf", 12)
UI_SMALL = ImageFont.truetype(FD + "DejaVuSans.ttf", 11)
UI_BOLD  = ImageFont.truetype(FD + "DejaVuSans-Bold.ttf", 11)
TINY     = ImageFont.truetype(FD + "DejaVuSans-Bold.ttf", 7)
MONO     = ImageFont.truetype(FD + "DejaVuSansMono.ttf", 12)

# ---------------------------------------------------------------- medidas
W, H = 860, 500
ACT_W, SIDE_W, TAB_H, STATUS_H = 46, 230, 32, 22
SIDE_X0, SIDE_X1 = ACT_W, ACT_W + SIDE_W
ED_X = SIDE_X1
GUTTER = 46
CODE_X = ED_X + GUTTER + 10
CODE_Y0 = TAB_H + 8
LINE_H = 18
STATUS_Y = H - STATUS_H
ROW_H, CH_H, MODEL_Y0 = 22, 20, 120
TARGET_SCROLL = 14

# ---------------------------------------------------------------- cores (VS Code Dark Modern)
C = {
    'act': (24, 24, 24), 'side': (24, 24, 24), 'editor': (31, 31, 31),
    'tab': (24, 24, 24), 'border': (43, 43, 43), 'status': (24, 24, 24),
    'text': (204, 204, 204), 'dim': (133, 133, 133), 'gutter': (110, 110, 110),
    'hover': (42, 45, 46), 'active': (55, 55, 61), 'sel': (38, 79, 120),
    'accent': (0, 120, 212), 'get': (86, 156, 214), 'set': (220, 150, 80),
    'kw': (86, 156, 214), 'str': (206, 145, 120), 'com': (106, 153, 85),
    'fn': (220, 220, 170), 'num': (181, 206, 168), 'var': (156, 220, 254),
    'plain': (212, 212, 212), 'ring': (90, 170, 240),
}

# ---------------------------------------------------------------- código de demonstração
# Ficheiro fictício (sem dados reais). As linhas são analisadas pela mesma lógica da extensão.
CODE = """sap.ui.define([
  "sap/ui/core/mvc/Controller",
  "sap/ui/model/json/JSONModel"
], function (Controller, JSONModel) {
  "use strict";

  return Controller.extend("demo.controller.Worklist", {

    onInit: function () {
      var oView = this.getView();
      var oColumns = { columns: [] };
      var oTasks = { items: [] };

      // this.getModel("OldModel");   <- comentário, não conta
      oView.setModel(new JSONModel(oColumns), "BoardColumns");
      oView.setModel(new JSONModel(oTasks), "Tasks");
      oView.setModel(new JSONModel({ count: 0 }), "TasksBoard");

      var oI18n = this.getModel("i18n");
      this.getOwnerComponent().setModel(new JSONModel({}), "NewTask");
    },

    onRefresh: function () {
      var oBoard = this.getModel("BoardColumns");
      oBoard.setProperty("/columns", []);

      var oTasks = this.getModel("Tasks");
      oTasks.setProperty("/items", []);
    },

    onBoardChange: function () {
      this.getModel("TasksBoard").refresh();
    },

    onNewTask: function () {
      var oNew = this.getModel("NewTask");
      oNew.setProperty("/title", "");
    }

  });
});"""
LINES = CODE.split("\n")


def parse(raw):
    """Mesma lógica do plugin: ignora comentários, apanha getModel/setModel com nome literal."""
    code = re.sub(r'/\*[\s\S]*?\*/|//[^\n]*', lambda m: re.sub(r'[^\n]', ' ', m.group(0)), raw)
    models = {}

    def add(name, kind, idx):
        line = code[:idx].count('\n') + 1
        m = models.setdefault(name, {'name': name, 'gets': [], 'sets': []})
        if line not in m[kind]:
            m[kind].append(line)

    for m in re.finditer(r'\.getModel\s*\(\s*["\']([^"\']+)["\']\s*\)', code):
        add(m.group(1), 'gets', m.start())
    for m in re.finditer(r'\.setModel\s*\([^;]*?,\s*["\']([^"\']+)["\']\s*\)', code):
        add(m.group(1), 'sets', m.start())
    return sorted(models.values(), key=lambda m: m['name'].lower())


MODELS = parse(CODE)
for _m in MODELS:
    _ch = [('get', l) for l in _m['gets']] + [('set', l) for l in _m['sets']]
    _m['children'] = sorted(_ch, key=lambda c: c[1])

STATUS_TOKENS = [
    ('icon', 'down'),
    ('text', ' ' + ', '.join(m['name'] for m in MODELS if m['gets'])),
    ('sep', '   |   '),
    ('icon', 'up'),
    ('text', ' ' + ', '.join(m['name'] for m in MODELS if m['sets'])),
]

# Tokenizador simples para colorir o código
TOK = re.compile(
    r'(//.*$)|("[^"]*")|(\b(?:var|function|return|this|new|const|let|true|false)\b)'
    r'|(\b\d+\b)|(\b[A-Za-z_]\w*(?=\())|(\b[A-Za-z_]\w*\b)|(\s+|.)'
)
TOK_KEY = {1: 'com', 2: 'str', 3: 'kw', 4: 'num', 5: 'fn', 6: 'var', 7: 'plain'}


def tokenize(line):
    return [(m.group(0), TOK_KEY[m.lastindex]) for m in TOK.finditer(line)]


# ---------------------------------------------------------------- utilidades de desenho
def txt(d, x, y, s, font, fill):
    d.text((int(round(x)), int(round(y))), s, font=font, fill=fill)


def blend(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def ease(t):
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def chevron(d, cx, cy, angle, col):
    th = math.radians(angle)
    c, s = math.cos(th), math.sin(th)
    pts = [(-3, -4), (3, 0), (-3, 4)]
    d.polygon([(cx + x * c - y * s, cy + x * s + y * c) for x, y in pts], fill=col)


def arrow(d, cx, cy, kind, s=4):
    if kind == 'down':
        d.polygon([(cx - s, cy - s + 1), (cx + s, cy - s + 1), (cx, cy + s)], fill=C['get'])
    else:
        d.polygon([(cx - s, cy + s - 1), (cx + s, cy + s - 1), (cx, cy - s)], fill=C['set'])


def db_icon(d, cx, cy, col):
    d.ellipse((cx - 5, cy - 6, cx + 5, cy - 2), outline=col)
    d.line((cx - 5, cy - 4, cx - 5, cy + 4), fill=col)
    d.line((cx + 5, cy - 4, cx + 5, cy + 4), fill=col)
    d.arc((cx - 5, cy, cx + 5, cy + 8), 0, 180, fill=col)


# ---------------------------------------------------------------- regiões da interface
def draw_activity(d):
    d.rectangle((0, 0, ACT_W - 1, STATUS_Y - 1), fill=C['act'])
    for i in range(5):
        cy = 28 + i * 44
        col = C['text'] if i == 0 else C['dim']
        d.rounded_rectangle((ACT_W // 2 - 9, cy - 9, ACT_W // 2 + 9, cy + 9), radius=3, outline=col, width=2)
    d.rectangle((0, 18, 2, 38), fill=C['text'])


def layout(expand):
    """Posições (centro vertical) das linhas da vista JSON MODELS."""
    pos = {}
    y = MODEL_Y0
    for m in MODELS:
        pos[('model', m['name'])] = y + ROW_H // 2
        y += ROW_H
        nv = int(expand.get(m['name'], 1.0) * len(m['children']) + 0.5)
        for j in range(nv):
            pos[('child', m['name'], j)] = y + CH_H // 2
            y += CH_H
    return pos


def draw_sidebar(d, expand, hover=None):
    d.rectangle((SIDE_X0, 0, SIDE_X1 - 1, STATUS_Y - 1), fill=C['side'])
    txt(d, SIDE_X0 + 16, 12, "EXPLORER", UI_SMALL, C['dim'])

    chevron(d, SIDE_X0 + 14, 43, 90, C['text'])
    txt(d, SIDE_X0 + 26, 36, "DEMO-APP", UI_BOLD, C['text'])

    d.rectangle((SIDE_X0, 60, SIDE_X1 - 1, 82), fill=C['active'])
    d.rectangle((SIDE_X0 + 28, 66, SIDE_X0 + 40, 78), fill=(241, 205, 58))
    txt(d, SIDE_X0 + 30, 68, "JS", TINY, (0, 0, 0))
    txt(d, SIDE_X0 + 48, 65, "Worklist.controller.js", UI, C['text'])

    chevron(d, SIDE_X0 + 14, 101, 90, C['text'])
    txt(d, SIDE_X0 + 26, 94, "JSON MODELS", UI_BOLD, C['text'])

    y = MODEL_Y0
    for m in MODELS:
        n = m['name']
        prog = expand.get(n, 1.0)
        cy = y + ROW_H // 2
        if hover == ('model', n):
            d.rectangle((SIDE_X0, y, SIDE_X1 - 1, y + ROW_H - 1), fill=C['hover'])
        chevron(d, SIDE_X0 + 16, cy, prog * 90, C['dim'])
        db_icon(d, SIDE_X0 + 36, cy, C['dim'])
        txt(d, SIDE_X0 + 50, y + 4, n, UI, C['text'])
        gx = SIDE_X1 - 78
        if m['gets']:
            arrow(d, gx + 5, cy, 'down')
            txt(d, gx + 13, y + 4, str(len(m['gets'])), UI, C['dim'])
        if m['sets']:
            arrow(d, gx + 36, cy, 'up')
            txt(d, gx + 44, y + 4, str(len(m['sets'])), UI, C['dim'])
        y += ROW_H

        nv = int(prog * len(m['children']) + 0.5)
        for j in range(nv):
            kind, line = m['children'][j]
            if hover == ('child', n, j):
                d.rectangle((SIDE_X0, y, SIDE_X1 - 1, y + CH_H - 1), fill=C['hover'])
            cy = y + CH_H // 2
            arrow(d, SIDE_X0 + 60, cy, 'down' if kind == 'get' else 'up')
            label = 'getModel' if kind == 'get' else 'setModel'
            col = C['get'] if kind == 'get' else C['set']
            txt(d, SIDE_X0 + 72, y + 3, label, UI_SMALL, col)
            txt(d, SIDE_X0 + 72 + UI_SMALL.getlength(label), y + 3,
                f" · linha {line}", UI_SMALL, C['dim'])
            y += CH_H

    d.line((SIDE_X1, 0, SIDE_X1, STATUS_Y), fill=C['border'])


def draw_editor(d, scroll, hl=None, hl_alpha=0.0):
    d.rectangle((ED_X, 0, W, STATUS_Y), fill=C['editor'])

    if hl is not None and hl_alpha > 0:
        hl_y = CODE_Y0 + (hl - 1 - scroll) * LINE_H
        d.rectangle((ED_X + GUTTER, hl_y, W, hl_y + LINE_H - 1),
                    fill=blend(C['editor'], C['sel'], hl_alpha))

    first = max(0, int(scroll))
    for i in range(first, min(len(LINES), first + 27)):
        y = CODE_Y0 + (i - scroll) * LINE_H
        if y > STATUS_Y or y < TAB_H - LINE_H:
            continue
        num = str(i + 1)
        numcol = C['text'] if hl == i + 1 else C['gutter']
        txt(d, ED_X + GUTTER - 10 - MONO.getlength(num), y + 2, num, MONO, numcol)
        x = CODE_X
        for s, key in tokenize(LINES[i]):
            txt(d, x, y + 2, s, MONO, C[key])
            x += MONO.getlength(s)

    # barra de separadores (desenhada por cima do código)
    d.rectangle((ED_X, 0, W, TAB_H - 1), fill=C['tab'])
    d.rectangle((ED_X, 0, ED_X + 200, TAB_H - 1), fill=C['editor'])
    d.rectangle((ED_X, 0, ED_X + 200, 1), fill=C['accent'])
    txt(d, ED_X + 14, 9, "Worklist.controller.js", UI, C['text'])
    d.line((ED_X, TAB_H - 1, W, TAB_H - 1), fill=C['border'])


def tokens_width():
    return sum(14 if k == 'icon' else UI.getlength(v) for k, v in STATUS_TOKENS)


def draw_status(d, reveal=None):
    d.rectangle((0, STATUS_Y, W, H), fill=C['status'])
    d.line((0, STATUS_Y, W, STATUS_Y), fill=C['border'])
    ty = STATUS_Y + 4
    x = W - tokens_width() - 14
    left = float('inf') if reveal is None else reveal
    for kind, val in STATUS_TOKENS:
        if kind == 'icon':
            if left > 0:
                arrow(d, x + 5, STATUS_Y + 11, val)
            x += 14
        elif kind == 'sep':
            if left > 0:
                txt(d, x, ty, val, UI, C['dim'])
            x += UI.getlength(val)
        else:
            if left > 0:
                txt(d, x, ty, val[:int(min(len(val), left))], UI, C['text'])
            left -= len(val)
            x += UI.getlength(val)


def render(reveal=None, expand=None, scroll=0.0, hl=None, hl_alpha=0.0,
           hover=None, ptr=None, click=None):
    if expand is None:
        expand = {m['name']: 1.0 for m in MODELS}
    img = Image.new('RGB', (W, H), C['editor'])
    d = ImageDraw.Draw(img)
    draw_activity(d)
    draw_sidebar(d, expand, hover)
    draw_editor(d, scroll, hl, hl_alpha)
    draw_status(d, reveal)
    if click:
        x, y, r = click
        d.ellipse((x - r, y - r, x + r, y + r), outline=C['ring'], width=2)
    if ptr:
        x, y = ptr
        d.polygon([(x, y), (x, y + 14), (x + 4, y + 10.5), (x + 6.8, y + 17),
                   (x + 9, y + 16), (x + 6.3, y + 9.8), (x + 11, y + 9.8)],
                  fill=(245, 245, 245), outline=(0, 0, 0))
    return img


# ---------------------------------------------------------------- cenas
def scene_barra():
    """01-barra: a barra de estado aparece com os modelos (efeito de escrita)."""
    F, D = [], []
    collapsed = {m['name']: 0.0 for m in MODELS}
    total = sum(len(v) for k, v in STATUS_TOKENS if k == 'text')
    F.append(render(reveal=0, expand=collapsed, scroll=12)); D.append(700)
    for k in range(1, total + 1, 2):
        F.append(render(reveal=k, expand=collapsed, scroll=12)); D.append(60)
    F.append(render(reveal=None, expand=collapsed, scroll=12)); D.append(3500)
    return F, D


def scene_vista():
    """02-vista: o rato expande cada modelo e as linhas aparecem."""
    F, D = [], []
    state = {m['name']: 0.0 for m in MODELS}
    px, py = 560, 330
    F.append(render(expand=state, ptr=(px, py))); D.append(600)
    for m in MODELS:
        n = m['name']
        pos = layout(state)
        tx, ty = SIDE_X0 + 80, pos[('model', n)]
        for t in range(1, 7):
            e = ease(t / 6)
            F.append(render(expand=state, ptr=(lerp(px, tx, e), lerp(py, ty, e)),
                            hover=('model', n))); D.append(45)
        px, py = tx, ty
        for r in (4, 9):
            F.append(render(expand=state, ptr=(px, py), hover=('model', n),
                            click=(px, py, r))); D.append(90)
        for t in range(1, 7):
            state[n] = ease(t / 6)
            F.append(render(expand=state, ptr=(px, py), hover=('model', n))); D.append(70)
        F.append(render(expand=state, ptr=(px, py))); D.append(300)
    D[-1] = 2500
    return F, D


def scene_clique():
    """03-clique: clique numa linha e o editor salta para o código."""
    F, D = [], []
    expand = {m['name']: 1.0 for m in MODELS}
    tasks = next(m for m in MODELS if m['name'] == 'Tasks')
    idx = next(j for j, (k, l) in enumerate(tasks['children']) if k == 'get' and l == 27)
    pos = layout(expand)
    tx, ty = SIDE_X0 + 90, pos[('child', 'Tasks', idx)]
    hov = ('child', 'Tasks', idx)

    px, py = 600, 320
    for t in range(1, 13):
        e = ease(t / 12)
        F.append(render(expand=expand, ptr=(lerp(px, tx, e), lerp(py, ty, e)))); D.append(40)
    px, py = tx, ty
    for _ in range(3):
        F.append(render(expand=expand, ptr=(px, py), hover=hov)); D.append(120)
    for r in (4, 10):
        F.append(render(expand=expand, ptr=(px, py), hover=hov, click=(px, py, r))); D.append(80)
    for t in range(1, 13):
        e = ease(t / 12)
        F.append(render(expand=expand, scroll=lerp(0, TARGET_SCROLL, e),
                        ptr=(px, py), hover=hov)); D.append(45)
    for t in range(1, 6):
        F.append(render(expand=expand, scroll=TARGET_SCROLL, hl=27, hl_alpha=t / 5,
                        ptr=(px, py))); D.append(60)
    F.append(render(expand=expand, scroll=TARGET_SCROLL, hl=27, hl_alpha=1.0, ptr=(px, py)))
    D.append(3000)
    return F, D


# ---------------------------------------------------------------- gravação
def save_gif(frames, durs, path):
    step = max(1, len(frames) // 12)
    sample = frames[::step]
    canvas = Image.new('RGB', (W, H * len(sample)))
    for i, f in enumerate(sample):
        canvas.paste(f, (0, i * H))
    ref = canvas.quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    out = [f.quantize(palette=ref, dither=Image.Dither.NONE) for f in frames]
    out[0].save(path, save_all=True, append_images=out[1:], duration=durs, loop=0)


if __name__ == '__main__':
    print("Modelos detetados:")
    for m in MODELS:
        print(f"  {m['name']:<12} get={m['gets']}  set={m['sets']}")
    print("Barra:", ' '.join(v for _, v in STATUS_TOKENS))

    scenes = [
        ('01-barra.gif', scene_barra),
        ('02-vista.gif', scene_vista),
        ('03-clique.gif', scene_clique),
    ]
    for name, fn in scenes:
        F, D = fn()
        path = os.path.join(OUT, name)
        save_gif(F, D, path)
        F[-1].save('/home/claude/preview-' + name.replace('.gif', '.png'))
        print(f"{name}: {len(F)} frames, {os.path.getsize(path) // 1024} KB")
