const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, BorderStyle, WidthType, ShadingType, HeadingLevel,
  PageNumberElement, NumberFormat, Header, Footer, TabStopType, TabStopPosition
} = require('docx');
const fs = require('fs');

// ---------------------------------------------------------------------------
// Template: Carta de Cessação de Contrato de Trabalho
// Placeholders are filled from template_data passed via JSON argument
// ---------------------------------------------------------------------------

const data = JSON.parse(process.argv[2] || '{}');

const D = (key, fallback = `{{${key}}}`) => data[key] || fallback;

const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };

function p(text, opts = {}) {
  return new Paragraph({
    alignment: opts.align || AlignmentType.JUSTIFIED,
    spacing: { before: opts.before || 0, after: opts.after || 160 },
    children: [new TextRun({
      text,
      bold:   opts.bold   || false,
      size:   opts.size   || 24,
      font:   "Arial",
      color:  opts.color  || "000000",
      italics: opts.italic || false,
    })]
  });
}

function pRuns(runs, opts = {}) {
  return new Paragraph({
    alignment: opts.align || AlignmentType.JUSTIFIED,
    spacing: { before: opts.before || 0, after: opts.after || 160 },
    children: runs.map(r => new TextRun({ font: "Arial", size: 24, ...r }))
  });
}

function spacer(n = 1) {
  return Array.from({ length: n }, () => new Paragraph({ children: [new TextRun({ text: "", size: 24 })] }));
}

function sectionTitle(text) {
  return new Paragraph({
    spacing: { before: 240, after: 120 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: "1a3a5c", space: 4 } },
    children: [new TextRun({ text, bold: true, size: 26, font: "Arial", color: "1a3a5c" })]
  });
}

function infoTable(rows) {
  return new Table({
    width: { size: 9026, type: WidthType.DXA },
    columnWidths: [3000, 6026],
    borders: { insideH: border, insideV: border, top: border, bottom: border, left: border, right: border },
    rows: rows.map(([label, value]) =>
      new TableRow({
        children: [
          new TableCell({
            borders,
            width: { size: 3000, type: WidthType.DXA },
            shading: { fill: "e8eef5", type: ShadingType.CLEAR },
            margins: { top: 80, bottom: 80, left: 120, right: 120 },
            children: [new Paragraph({ children: [new TextRun({ text: label, bold: true, size: 22, font: "Arial", color: "1a3a5c" })] })]
          }),
          new TableCell({
            borders,
            width: { size: 6026, type: WidthType.DXA },
            margins: { top: 80, bottom: 80, left: 120, right: 120 },
            children: [new Paragraph({ children: [new TextRun({ text: value, size: 22, font: "Arial" })] })]
          })
        ]
      })
    )
  });
}

// ---------------------------------------------------------------------------
// Document
// ---------------------------------------------------------------------------

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 24 } } }
  },
  sections: [{
    properties: {
      page: {
        size: { width: 11906, height: 16838 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1800 }
      }
    },
    headers: {
      default: new Header({
        children: [
          new Paragraph({
            border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: "1a3a5c", space: 4 } },
            spacing: { after: 80 },
            children: [
              new TextRun({ text: D("nome_escritorio", "Escritório de Advocacia"), bold: true, size: 22, font: "Arial", color: "1a3a5c" }),
              new TextRun({ text: "   |   Ref.: " + D("referencia_processo", "—"), size: 20, font: "Arial", color: "666666" }),
            ]
          })
        ]
      })
    },
    footers: {
      default: new Footer({
        children: [
          new Paragraph({
            border: { top: { style: BorderStyle.SINGLE, size: 2, color: "cccccc", space: 4 } },
            spacing: { before: 80 },
            tabStops: [{ type: TabStopType.RIGHT, position: TabStopPosition.MAX }],
            children: [
              new TextRun({ text: "Documento gerado por AIAA — Assistente Jurídico", size: 18, font: "Arial", color: "999999", italics: true }),
              new TextRun({ text: "\t", size: 18 }),
              new TextRun({ text: "Documento confidencial", size: 18, font: "Arial", color: "999999" }),
            ]
          })
        ]
      })
    },
    children: [

      // ── Título ──────────────────────────────────────────────────────────
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 240, after: 80 },
        children: [new TextRun({ text: "CARTA DE CESSAÇÃO DE CONTRATO DE TRABALHO", bold: true, size: 30, font: "Arial", color: "1a3a5c" })]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 0, after: 320 },
        children: [new TextRun({ text: "Por " + D("motivo_cessacao", "Justa Causa Disciplinar"), size: 24, font: "Arial", color: "444444", italics: true })]
      }),

      // ── Dados da Entidade Empregadora ────────────────────────────────────
      sectionTitle("I. ENTIDADE EMPREGADORA"),
      ...spacer(1),
      infoTable([
        ["Denominação",      D("nome_empregador")],
        ["NIF",              D("nif_empregador")],
        ["Sede Social",      D("morada_empregador")],
        ["Representante",    D("representante_empregador")],
        ["Cargo",            D("cargo_representante")],
      ]),
      ...spacer(1),

      // ── Dados do Trabalhador ─────────────────────────────────────────────
      sectionTitle("II. TRABALHADOR"),
      ...spacer(1),
      infoTable([
        ["Nome Completo",    D("nome_trabalhador")],
        ["NIF",              D("nif_trabalhador")],
        ["Morada",           D("morada_trabalhador")],
        ["Categoria",        D("categoria_profissional")],
        ["Data de Admissão", D("data_admissao")],
        ["Nº de Contrato",   D("numero_contrato")],
      ]),
      ...spacer(1),

      // ── Fundamentação ────────────────────────────────────────────────────
      sectionTitle("III. FUNDAMENTAÇÃO JURÍDICA"),
      ...spacer(1),
      p("Nos termos do artigo 351.º do Código do Trabalho, aprovado pela Lei n.º 7/2009, de 12 de fevereiro, constitui justa causa de despedimento o comportamento culposo do trabalhador que, pela sua gravidade e consequências, torne imediata e praticamente impossível a subsistência da relação de trabalho.", { after: 200 }),
      p("Com fundamento no disposto no artigo 329.º do Código do Trabalho, o procedimento disciplinar foi instaurado dentro do prazo de 60 dias a contar do conhecimento dos factos pela entidade empregadora.", { after: 200 }),
      p(D("fundamentacao_factual", "Os factos imputados ao trabalhador, devidamente apurados em procedimento disciplinar, são os seguintes:"), { after: 200 }),
      new Paragraph({
        spacing: { before: 0, after: 200 },
        indent: { left: 720 },
        children: [new TextRun({ text: D("descricao_factos", "Descrever os factos apurados no procedimento disciplinar."), size: 24, font: "Arial", italics: true, color: "444444" })]
      }),
      ...spacer(1),

      // ── Decisão ──────────────────────────────────────────────────────────
      sectionTitle("IV. DECISÃO"),
      ...spacer(1),
      pRuns([
        { text: "Face ao exposto, e ao abrigo do artigo " },
        { text: D("artigo_cessacao", "351.º e 357.º"), bold: true },
        { text: " do Código do Trabalho, a entidade empregadora decide proceder ao " },
        { text: "despedimento com justa causa", bold: true },
        { text: " do(a) trabalhador(a) " },
        { text: D("nome_trabalhador"), bold: true },
        { text: ", com efeitos a partir de " },
        { text: D("data_efeitos", "{{data_efeitos}}"), bold: true },
        { text: "." },
      ], { after: 200 }),
      p("O trabalhador tem direito a receber os créditos laborais vencidos e exigíveis, incluindo proporcionais de férias, subsídio de férias e subsídio de Natal, calculados até à data da cessação do contrato.", { after: 200 }),
      p("Nos termos do artigo 389.º do Código do Trabalho, caso o despedimento venha a ser declarado ilícito, o trabalhador poderá optar entre a reintegração ou uma indemnização nos termos do artigo 391.º do mesmo diploma.", { after: 200 }),
      ...spacer(1),

      // ── Notificação ──────────────────────────────────────────────────────
      sectionTitle("V. NOTIFICAÇÃO"),
      ...spacer(1),
      p("O(A) trabalhador(a) é notificado(a) da presente decisão, nos termos do artigo 357.º, n.º 5 do Código do Trabalho, ficando ciente de que pode impugnar judicialmente o presente despedimento no prazo de 60 dias a contar da recepção desta carta, junto do Tribunal do Trabalho competente.", { after: 200 }),
      ...spacer(2),

      // ── Assinatura ───────────────────────────────────────────────────────
      new Paragraph({
        alignment: AlignmentType.RIGHT,
        spacing: { before: 0, after: 80 },
        children: [new TextRun({ text: D("local_data", "Lisboa, ____ de __________ de 2024"), size: 22, font: "Arial" })]
      }),
      ...spacer(2),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 0, after: 80 },
        border: { top: { style: BorderStyle.SINGLE, size: 2, color: "cccccc", space: 8 } },
        children: [new TextRun({ text: D("representante_empregador", "Assinatura do Representante"), size: 22, font: "Arial" })]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 0, after: 320 },
        children: [new TextRun({ text: D("nome_empregador", "Entidade Empregadora"), size: 20, font: "Arial", color: "666666" })]
      }),

      // ── Aviso Legal ──────────────────────────────────────────────────────
      new Paragraph({
        spacing: { before: 320, after: 80 },
        border: { top: { style: BorderStyle.SINGLE, size: 2, color: "cccccc", space: 6 } },
        children: [new TextRun({ text: "AVISO: Este documento foi gerado com apoio do sistema AIAA e deve ser revisto por advogado habilitado antes de ser utilizado. As referências legais são indicativas e devem ser verificadas face à legislação em vigor.", size: 18, font: "Arial", color: "888888", italics: true })]
      }),
    ]
  }]
});

Packer.toBuffer(doc).then(buf => {
  const out = process.argv[3] || "peca_juridica.docx";
  fs.writeFileSync(out, buf);
  console.log("OK:" + out);
});
