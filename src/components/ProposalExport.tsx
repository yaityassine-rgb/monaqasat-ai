import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Download, FileText, Loader2 } from "lucide-react";
import { Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType } from "docx";
import { saveAs } from "file-saver";

interface ProposalSection {
  key: string;
  title: string;
  content: string;
  status: string;
}

interface Proposal {
  id: string;
  title: string;
  language: string;
  sections: ProposalSection[];
}

export default function ProposalExport({ proposal }: { proposal: Proposal }) {
  const { t } = useTranslation();
  const [exporting, setExporting] = useState<string | null>(null);

  const isRTL = proposal.language === "ar";
  const readySections = (proposal.sections as ProposalSection[]).filter(
    (s) => s.status === "ready" && s.content
  );

  const exportDOCX = async () => {
    setExporting("docx");

    try {
      const children: Paragraph[] = [];

      // Title
      children.push(
        new Paragraph({
          children: [
            new TextRun({
              text: proposal.title,
              bold: true,
              size: 32,
              font: isRTL ? "Arial" : "Calibri",
            }),
          ],
          heading: HeadingLevel.TITLE,
          alignment: isRTL ? AlignmentType.RIGHT : AlignmentType.LEFT,
          spacing: { after: 400 },
        })
      );

      // Sections
      for (const section of readySections) {
        // Section heading
        children.push(
          new Paragraph({
            children: [
              new TextRun({
                text: section.title,
                bold: true,
                size: 26,
                font: isRTL ? "Arial" : "Calibri",
              }),
            ],
            heading: HeadingLevel.HEADING_1,
            alignment: isRTL ? AlignmentType.RIGHT : AlignmentType.LEFT,
            spacing: { before: 400, after: 200 },
          })
        );

        // Section content - split by paragraphs
        const paragraphs = section.content.split("\n\n");
        for (const para of paragraphs) {
          if (para.trim()) {
            children.push(
              new Paragraph({
                children: [
                  new TextRun({
                    text: para.trim(),
                    size: 22,
                    font: isRTL ? "Arial" : "Calibri",
                  }),
                ],
                alignment: isRTL ? AlignmentType.RIGHT : AlignmentType.LEFT,
                spacing: { after: 200 },
                bidirectional: isRTL,
              })
            );
          }
        }
      }

      const doc = new Document({
        sections: [
          {
            properties: {
              page: {
                margin: {
                  top: 1440,
                  right: 1440,
                  bottom: 1440,
                  left: 1440,
                },
              },
            },
            children,
          },
        ],
      });

      const blob = await Packer.toBlob(doc);
      const fileName = `${proposal.title.replace(/[^a-zA-Z0-9\u0600-\u06FF ]/g, "_")}.docx`;
      saveAs(blob, fileName);
    } catch (err) {
      console.error("DOCX export error:", err);
    }

    setExporting(null);
  };

  const exportTXT = () => {
    setExporting("txt");

    const lines: string[] = [proposal.title, "=".repeat(proposal.title.length), ""];

    for (const section of readySections) {
      lines.push(section.title);
      lines.push("-".repeat(section.title.length));
      lines.push("");
      lines.push(section.content);
      lines.push("");
      lines.push("");
    }

    const blob = new Blob([lines.join("\n")], { type: "text/plain;charset=utf-8" });
    const fileName = `${proposal.title.replace(/[^a-zA-Z0-9\u0600-\u06FF ]/g, "_")}.txt`;
    saveAs(blob, fileName);

    setExporting(null);
  };

  const printPDF = () => {
    // Open print dialog — cleanest cross-browser PDF approach with full Arabic support
    const printWindow = window.open("", "_blank");
    if (!printWindow) return;

    const sectionsHTML = readySections
      .map(
        (s) => `
        <h2 style="color: #1e293b; border-bottom: 2px solid #3b82f6; padding-bottom: 8px; margin-top: 32px;">
          ${s.title}
        </h2>
        <div style="white-space: pre-wrap; line-height: 1.8; color: #334155;">
          ${s.content}
        </div>`
      )
      .join("");

    printWindow.document.write(`<!DOCTYPE html>
<html dir="${isRTL ? "rtl" : "ltr"}" lang="${proposal.language}">
<head>
  <meta charset="utf-8">
  <title>${proposal.title}</title>
  <style>
    body { font-family: ${isRTL ? "'Arial', 'Tahoma'" : "'Calibri', 'Segoe UI'"}, sans-serif; max-width: 700px; margin: 40px auto; padding: 0 20px; color: #1e293b; }
    h1 { font-size: 24px; color: #0f172a; margin-bottom: 4px; }
    h2 { font-size: 18px; }
    @media print { body { margin: 0; padding: 20px; } }
  </style>
</head>
<body>
  <h1>${proposal.title}</h1>
  <hr style="border: 1px solid #e2e8f0; margin: 16px 0;">
  ${sectionsHTML}
  <div style="margin-top: 40px; text-align: center; color: #94a3b8; font-size: 12px;">
    Generated by Monaqasat AI
  </div>
</body>
</html>`);

    printWindow.document.close();
    setTimeout(() => printWindow.print(), 500);
  };

  if (readySections.length === 0) {
    return (
      <div className="glass-card rounded-xl p-4 text-center">
        <p className="text-sm text-slate-400">{t("proposals.noSectionsToExport")}</p>
      </div>
    );
  }

  return (
    <div className="glass-card rounded-xl p-4">
      <h3 className="text-sm font-semibold text-white mb-3">
        {t("proposals.exportAs")}
      </h3>
      <div className="flex flex-wrap gap-2">
        <button
          onClick={exportDOCX}
          disabled={exporting === "docx"}
          className="flex items-center gap-2 px-4 py-2 bg-blue-500/10 text-blue-400 text-sm rounded-lg hover:bg-blue-500/20 transition-colors disabled:opacity-50"
        >
          {exporting === "docx" ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <FileText className="w-4 h-4" />
          )}
          DOCX
        </button>

        <button
          onClick={printPDF}
          className="flex items-center gap-2 px-4 py-2 bg-red-500/10 text-red-400 text-sm rounded-lg hover:bg-red-500/20 transition-colors"
        >
          <Download className="w-4 h-4" />
          PDF
        </button>

        <button
          onClick={exportTXT}
          disabled={exporting === "txt"}
          className="flex items-center gap-2 px-4 py-2 bg-slate-500/10 text-slate-400 text-sm rounded-lg hover:bg-slate-500/20 transition-colors disabled:opacity-50"
        >
          <FileText className="w-4 h-4" />
          TXT
        </button>
      </div>
      <p className="text-xs text-slate-500 mt-2">
        {readySections.length} {t("proposals.sectionsReady")}
      </p>
    </div>
  );
}
