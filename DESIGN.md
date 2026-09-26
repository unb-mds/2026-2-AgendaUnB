---
name: Agenda UnB
description: Hub digital acadêmico e extracurricular da Universidade de Brasília.
colors:
  primary: "#008bff"
  primary-deep: "rgba(0, 95, 210, 1)"
  bg-dark: "#050508"
  surface-glass: "rgba(8, 12, 22, 0.78)"
  surface-input: "rgba(0, 15, 35, 0.6)"
  text-high: "#ffffff"
  text-medium: "rgba(255, 255, 255, 0.55)"
  text-muted: "rgba(255, 255, 255, 0.35)"
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
    backgroundColor: "{colors.surface-input}"
    textColor: "{colors.text-high}"
    rounded: "{rounded.sm}"
    padding: "13px 16px"
---

# Design System: Agenda UnB

## Overview

**Creative North Star: "The Neon Campus"**

A identidade visual da Agenda UnB mescla o rigor acadêmico com um futurismo digital sutil. A interface abandona as clássicas telas brancas institucionais e adota uma estética predominantemente *dark*, focada no alto contraste e na modernidade. O uso intenso de *glassmorphism* (fundo translúcido e desfoque) cria camadas de profundidade, enquanto os toques brilhantes do azul iluminam pontos de interação.

**Key Characteristics:**
- **Atmosfera noturna:** Fundo super escuro, quase preto absoluto.
- **Translucidez:** Modais, navbars e cards deixam o fundo vazar levemente através do `backdrop-filter`.
- **Brilhos em vez de sombras:** Os efeitos de profundidade são alcançados com sombras azuis que emulam luzes neon ou "glow".
- **Tipografia Sci-Fi:** Títulos utilizam a fonte Orbitron para dar um toque tecnológico.

## Colors

A paleta é contida e focada, usando o azul como grande protagonista contra o abismo escuro do fundo.

### Primary
- **Azul UnB Glow** (#008bff): A cor vital do projeto. Usada em avatares, bordas de interação, rótulos e efeitos de brilho/sombra.
- **Azul Deep** (rgba(0, 95, 210, 1)): Versão ligeiramente mais fechada, usada como fundo sólido de botões primários.

### Neutral
- **Void Background** (#050508): Fundo raiz da aplicação.
- **Glass Surface** (rgba(8, 12, 22, 0.78)): Fundo semi-transparente usado para modais e cards flutuantes.
- **White High** (#ffffff): Texto principal e ícones ativos.
- **White Medium** (rgba(255, 255, 255, 0.55)): Texto de apoio, subtítulos e placeholders.

### Named Rules
**The Glow-Over-Shadow Rule.** Em vez de usar sombras pretas para separar componentes do fundo, usamos o azul (`rgba(0, 139, 255, 0.12)`) para criar um aspecto de luz emitindo da borda do componente, especialmente em estados de *hover*.

## Typography

**Display Font:** Orbitron
**Body Font:** Inter

**Character:** A Orbitron traz uma personalidade digital marcante para cabeçalhos e logo, enquanto a Inter segura a carga cognitiva pesada das descrições de eventos e formulários com extrema legibilidade.

### Hierarchy
- **Display** (700, clamp(1.6rem, 3.5vw, 2.2rem)): Títulos de seções (`.section-h2`).
- **Title** (600, 1.05rem): Títulos de cards e destaques menores.
- **Body** (400, 0.88rem - 0.95rem): Textos descritivos, subtítulos e leitura longa.
- **Label** (600/700, 0.78rem, uppercase, 0.05em): Rótulos de inputs, categorias e *badges*.

## Elevation & Depth

O sistema depende majoritariamente de **Glassmorphism** e **Neon Glow** em vez de elevação clássica material.

### Shadow Vocabulary
- **Glow Hover** (`0 8px 32px rgba(0,139,255,0.12)`): Aplicado aos cards e botões interativos ao passar o mouse.
- **Modal Shadow** (`0 20px 50px rgba(0,0,0,0.8), 0 0 35px rgba(0,139,255,0.2)`): Sombreamento forte e misto para isolar completamente o modal do resto do site.

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
- **Style:** Fundo translúcido escuro (`rgba(0, 15, 35, 0.6)`) com borda fina azulada.
- **Focus:** A borda fica opaca (`rgba(0, 139, 255, 0.8)`) e emite um glow sutil (`box-shadow: 0 0 12px rgba(0, 139, 255, 0.3)`).

### Feature Cards
- **Corner Style:** Suave (14px).
- **Background:** Vidro escuro (`rgba(8,12,22,0.65)`) com `backdrop-filter: blur(8px)`.
- **Border:** `1px solid rgba(0,139,255,0.12)`.
- **Interação:** Ao fazer *hover*, o card translada 4px para cima, a borda acende (`0.5`) e a sombra azul aparece.

## Do's and Don'ts

### Do:
- **Do** manter a legibilidade dos textos mesmo sobre áreas com *blur*.
- **Do** usar o azul `#008bff` com parcimônia para que ele retenha seu valor de CTA e destaque.

### Don't:
- **Don't** utilizar sombras pretas duras para destacar elementos dentro dos cards; confie na opacidade dos textos.
- **Don't** quebrar o isolamento do modal com cores sólidas e opacas que destruam a sensação de vidro.
- **Don't** utilizar emojis como ícones ou elementos de interface (UI). Toda a iconografia deve ser feita através da biblioteca Material Symbols.
- **Don't** utilizar estilos com bordas coloridas acompanhadas de background mais claro (ex: fundo azul claro com borda e texto azuis), pois não passam a personalidade do produto.
- **Don't** aplicar *linear gradients* em nenhum contexto de UI (fundos, botões, ícones ou textos). Use sempre cores sólidas que suportem a linguagem visual clara e limpa.
- **Don't** ultrapassar 20% de opacidade em sombras pretas (`rgba(0,0,0,0.2)`). Evite sombras pesadas para simular elevação e, em vez disso, conte com o *backdrop-filter* (vidro) e o *glow* (sombra azul clara ou colorida) para gerar separação e hierarquia.
