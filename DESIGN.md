---
name: Agenda UnB
description: Hub digital acadêmico e extracurricular da Universidade de Brasília.
colors:
  primary: "#008bff"
  primary-deep: "rgba(0, 95, 210, 1)"
  accent-fill: "#0273ec"
  on-accent-fill: "#ffffff"
  bg-dark: "#080c16"
  bg-dark-canvas: "#050508"
  surface-card-dark: "#1a2235"
  surface-input-dark: "#101a2c"
  surface-glass-dark: "rgba(8, 12, 22, 0.78)"
  surface-glass-plans-dark: "rgba(12, 18, 32, 0.78)"
  border-dark: "rgba(255, 255, 255, 0.15)"
  text-high-dark: "#ffffff"
  text-muted-dark: "#94a3b8"
  bg-light: "#f0f4f8"
  bg-light-canvas: "#f5f6fa"
  surface-card-light: "#ffffff"
  surface-input-light: "#f8fafc"
  surface-glass-light: "rgba(255, 255, 255, 0.85)"
  border-light: "rgba(0, 0, 0, 0.15)"
  text-high-light: "#1a1a2e"
  text-muted-light: "#526278"
typography:
  display:
    fontFamily: "'Orbitron', sans-serif"
    fontWeight: 700
    letterSpacing: "0.03em"
  body:
    fontFamily: "'Inter', sans-serif"
    fontWeight: 400
  label:
    fontFamily: "'Inter', sans-serif"
    fontWeight: 600
    letterSpacing: "0.05em"
    textTransform: "uppercase"
rounded:
  sm: "10px"
  md: "14px"
  lg: "20px"
  pill: "999px"
  full: "50%"
spacing:
  xs: "6px"
  sm: "16px"
  md: "24px"
  lg: "36px"
components:
  button-primary:
    backgroundColor: "{colors.primary-deep}"
    textColor: "{colors.text-high}"
    rounded: "{rounded.sm}"
    padding: "14px"
  input-field:
    backgroundColor: "{colors.surface-input-dark}"
    textColor: "{colors.text-high-dark}"
    rounded: "{rounded.sm}"
    padding: "13px 16px"
---

# Design System: Agenda UnB

## Overview

**Creative North Star: "The Neon Campus"**

A identidade visual da Agenda UnB mescla rigor acadêmico com futurismo digital sutil e bivalência nativa entre **Modo Escuro (Dark)** e **Modo Claro (Light)**. O uso de *glassmorphism* neutro, bordas sutis e superfícies planas (*flat*) cria camadas de profundidade, enquanto o azul `#008bff` ilumina pontos de interação e chamadas para ação.

**Key Characteristics:**
- **Bivalência Dark / Light:** Páginas internas operam com base `#080c16` (Dark) e `#f0f4f8` (Light), enquanto a página inicial e a página de detalhes de evento utilizam variantes de canvas (`#050508` no Dark e `#f5f6fa` no Light).
- **Translucidez:** Modais, navbars e superfícies hero/planos utilizam *glassmorphism* via `backdrop-filter`.
- **Brilhos em vez de sombras pesadas:** A separação visual prioriza bordas sutis e sombras azuis (*glow*) em vez de sombras pretas densas em cards.
- **Tipografia Sci-Fi + Legibilidade:** Títulos de destaque usam a fonte Orbitron; corpo de texto e formulários usam Inter.

## Colors

A paleta é contida e focada, usando o azul como grande protagonista em ambos os temas.

### Primary
- **Azul UnB Glow** (`#008bff`): A cor vital do projeto. Usada em avatares, bordas de interação, rótulos e efeitos de brilho.
- **Azul Deep** (`rgba(0, 95, 210, 1)` / `#005fd2`): Versão ligeiramente mais fechada, usada em botões primários e destaques de contraste.
- **Preenchimento azul** (`--accent-fill`, `#0273ec`): Use em seleções ativas, marcas de seleção, destaques do calendário e ações como **Criar Evento**, com texto e ícones brancos (`--on-accent-fill`, `#ffffff`) nos dois temas. O tom é a cor sRGB de 8 bits mais próxima de `#008bff` pela distância euclidiana em OKLab entre as que atingem WCAG AA para texto comum em branco. O par sólido atinge **4,500546:1**. [WCAG 2.1 AA — contraste mínimo](https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html)
- **Ações de gestão e Planos de ensino:** Os botões primários, incluindo **Seguir turmas**, usam `--accent-fill` por meio de `--manage-action`.
- **Ícones de cards no tema escuro:** Na página inicial, os ícones são pretos sobre fundo azul. Em **Selecionar turmas** e **Organizar datas**, os ícones são brancos. O fundo do ícone da etapa ativa é `#0273ec` e o da etapa inativa é `#30659e1e`, um azul com cerca de 12% de opacidade sobre o card.

### Dark Mode
- **App Background** (`#080c16`): Fundo das páginas internas (agenda, planos, moderação, administração e configurações).
- **Canvas / Hero Background** (`#050508`): Fundo da landing page e da página de detalhes de evento.
- **Card Surface** (`#1a2235`): Fundo sólido dos cards nas páginas internas.
- **Input Surface** (`#101a2c`): Fundo padrão de campos de formulário nas páginas internas (`rgba(6, 12, 24, 0.68)` na área de planos).
- **Glass Surface** (`rgba(8, 12, 22, 0.78)` / `rgba(8, 12, 22, 0.65)` na landing / `rgba(12, 18, 32, 0.78)` em planos): Fundos semi-transparentes para modais, cartões de destaque e superfícies translúcidas.
- **Text High** (`#ffffff`) e **Text Muted** (`#94a3b8`), com bordas `rgba(255, 255, 255, 0.15)`.

### Light Mode
- **App Background** (`#f0f4f8`): Fundo das páginas internas (agenda, gestão e planos).
- **Canvas / Hero Background** (`#f5f6fa`): Fundo da landing page e da página de detalhes de evento.
- **Card Surface** (`#ffffff`) e **Glass Surface** (`rgba(255, 255, 255, 0.85)`): Fundos de cards e painéis de ação.
- **Input Surface** (`#f8fafc` / `#f4f7fb` em planos): Fundos de campos de formulário.
- **Text High** (`#1a1a2e`) e **Text Muted** (`#526278`), com bordas `rgba(0, 0, 0, 0.15)`.

### Named Rules
**The Glow-Over-Shadow Rule.** Em vez de usar sombras pretas para separar componentes do fundo, usamos o azul (`rgba(0, 139, 255, 0.12)`) para criar um aspecto de luz emitindo da borda do componente, especialmente em estados de *hover*.

## Typography

**Display Font:** Orbitron
**Body Font:** Inter

**Character:** A Orbitron traz uma personalidade digital marcante para cabeçalhos e logo, enquanto a Inter segura a carga cognitiva pesada das descrições de eventos e formulários com extrema legibilidade.

**Marca na navegação:** A ampulheta original acompanha o nome “Agenda UnB” em Orbitron sem itálico.

### Hierarchy
- **Display** (700, clamp(1.6rem, 3.5vw, 2.2rem)): Títulos de seções (`.section-h2`).
- **Title** (600, 1.05rem): Títulos de cards e destaques menores.
- **Body** (400, 0.88rem - 0.95rem): Textos descritivos, subtítulos e leitura longa.
- **Label** (600/700, 0.78rem, uppercase, 0.05em): Rótulos de inputs, categorias e *badges*.

## Elevation & Depth

O sistema depende majoritariamente de **Glassmorphism** e **Neon Glow** em vez de elevação clássica material.

### Shadow Vocabulary
- **Glow Hover** (`0 8px 32px rgba(0,139,255,0.12)` / `0 4px 20px rgba(0,139,255,0.09)`): Aplicado aos cards e botões interativos.
- **Modal Shadow** (`0 20px 50px rgba(0,0,0,0.2), 0 0 35px rgba(0,139,255,0.2)` / `0 20px 50px rgba(0,0,0,0.18)` em modais de gestão): Sombreamento controlado de até 20% na sombra preta combinado a *glow* azul.
- **Exceções intencionais (Backdrops e Neon Glow):** Overlays de fundo de modal (`rgba(2, 6, 16, 0.88)`, `rgba(0, 0, 0, 0.75)` a `0.8`, e `rgb(223 232 244 / 75%)` no modo claro) e brilhos neon azuis (`rgba(0, 139, 255, 0.25)` a `0.45`) em hover/foco/CTAs constituem exceções documentadas à regra geral de 20% para sombras pretas de cards.

## Shapes

A linguagem de formas mistura raios suaves e formas orgânicas de pílula.

- **Pílulas (999px):** Utilizada na Navbar principal, botões de filtro e *badges* de categorias.
- **Cards & Modais (14px a 20px):** Caixas flutuantes possuem raios de borda moderados e sempre vêm acompanhados de uma borda fina sutil (`1px solid rgba(0, 139, 255, 0.12)`).
- **Inputs (10px):** Formas mais utilitárias para campos de digitação.

## Components

### Botões Primários
- **Shape:** Arredondado (10px).
- **Primary:** Azul sólido escuro com texto branco.
- **Hover / Focus:** Transições suaves com acréscimo de glow azul (`box-shadow: 0 4px 20px rgba(0, 139, 255, 0.35)`).

### Inputs / Fields
- **Style:** Fundo `#101a2c` (Dark) / `#f8fafc` (Light) nas páginas internas e superfície translúcida escura (`rgba(6, 12, 24, 0.68)`) na área de planos, com borda fina sutil.
- **Focus:** A borda fica destacada (`rgba(0, 139, 255, 0.8)`) e emite um glow sutil (`box-shadow: 0 0 12px rgba(0, 139, 255, 0.3)`).

### Feature Cards
- **Corner Style:** Suave (14px).
- **Background:** Sólido `#1a2235` (Dark) / `#ffffff` (Light) nas páginas internas; vidro `rgba(8,12,22,0.65)` (Dark) / `rgba(255,255,255,0.85)` (Light) com `backdrop-filter: blur(8px)` na landing.
- **Border:** `1px solid rgba(255,255,255,0.15)` (Dark) / `1px solid rgba(0,0,0,0.15)` (Light), com destaque azul (`rgba(0,139,255,0.12)` a `0.5`) em interação.
- **Interação:** Ao fazer *hover*, o card translada suavemente, a borda acende e o *glow* azul aparece.

## Do's and Don'ts

### Do:
- **Do** manter a legibilidade dos textos mesmo sobre áreas com *blur*.
- **Do** usar `#008bff` com parcimônia em acentos e focos. Use `#0273ec` como fundo sólido com texto branco nos controles que adotam o tom de preenchimento.

### Don't:
- **Don't** utilizar sombras pretas duras para destacar elementos dentro dos cards; confie na opacidade dos textos.
- **Don't** quebrar o isolamento do modal com cores sólidas e opacas que destruam a sensação de vidro.
- **Don't** utilizar emojis como ícones ou elementos de interface (UI). Toda a iconografia deve ser feita através da biblioteca Material Symbols.
- **Don't** utilizar estilos com bordas coloridas acompanhadas de background mais claro (ex: fundo azul claro com borda e texto azuis), pois não passam a personalidade do produto.
- **Don't** aplicar *linear gradients* em nenhum contexto de UI (fundos, botões, ícones ou textos). Use sempre cores sólidas que suportem a linguagem visual clara e limpa.
- **Don't** ultrapassar 20% de opacidade em sombras pretas de cards (`rgba(0,0,0,0.2)`), reservando opacidades maiores apenas às exceções documentadas de backdrops de modais/overlays e *glows* azuis. Evite sombras pesadas para simular elevação e, em vez disso, conte com o *backdrop-filter* (vidro) e o *glow* (sombra azul) para gerar separação e hierarquia.
