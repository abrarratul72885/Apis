"""Tiny Excel (.xlsx) writer using only the standard library."""
import io
import re
import zipfile
from xml.sax.saxutils import escape

_BAD = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _col(i):
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def _text(v):
    return escape(_BAD.sub("", str(v)))


def _sheet_xml(headers, rows):
    widths = [max(10, min(60, len(str(h)) + 3)) for h in headers]
    for row in rows:
        for i, v in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], min(60, len(str(v).split("\n")[0]) + 2))
    out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
           '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
           '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>',
           "<cols>"]
    for i, w in enumerate(widths):
        out.append('<col min="%d" max="%d" width="%d" customWidth="1"/>' % (i + 1, i + 1, w))
    out.append("</cols><sheetData>")
    out.append('<row r="1">')
    for i, h in enumerate(headers):
        out.append('<c r="%s1" s="1" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>' % (_col(i), _text(h)))
    out.append("</row>")
    for r, row in enumerate(rows, start=2):
        out.append('<row r="%d">' % r)
        for i, v in enumerate(row):
            ref = "%s%d" % (_col(i), r)
            if v is None or v == "":
                continue
            if isinstance(v, bool):
                out.append('<c r="%s" t="inlineStr"><is><t>%s</t></is></c>' % (ref, "Yes" if v else "No"))
            elif isinstance(v, (int, float)):
                out.append('<c r="%s"><v>%s</v></c>' % (ref, repr(float(v)) if isinstance(v, float) else v))
            else:
                out.append('<c r="%s" s="2" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>' % (ref, _text(v)))
        out.append("</row>")
    out.append("</sheetData>")
    if rows:
        out.append('<autoFilter ref="A1:%s%d"/>' % (_col(len(headers) - 1), len(rows) + 1))
    out.append("</worksheet>")
    return "".join(out)


STYLES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font>'
    '<font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font></fonts>'
    '<fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill>'
    '<fill><patternFill patternType="solid"><fgColor rgb="FF0B57D0"/><bgColor indexed="64"/></patternFill></fill></fills>'
    '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
    '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
    '<cellXfs count="3"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
    '<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/>'
    '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>'
    '</cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>'
)


def build(sheets):
    """sheets: list of (name, headers, rows). Returns bytes of an .xlsx file."""
    buf = io.BytesIO()
    names = []
    for name, _h, _r in sheets:
        clean = re.sub(r"[\[\]:*?/\\]", " ", name)[:31] or "Sheet"
        names.append(clean)
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        ct = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
              '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
              '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
              '<Default Extension="xml" ContentType="application/xml"/>',
              '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
              '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>']
        for i in range(len(sheets)):
            ct.append('<Override PartName="/xl/worksheets/sheet%d.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' % (i + 1))
        ct.append("</Types>")
        z.writestr("[Content_Types].xml", "".join(ct))
        z.writestr("_rels/.rels",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        wb = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
              '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>']
        rel = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
               '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">']
        for i, n in enumerate(names):
            wb.append('<sheet name="%s" sheetId="%d" r:id="rId%d"/>' % (escape(n, {'"': "&quot;"}), i + 1, i + 1))
            rel.append('<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet%d.xml"/>' % (i + 1, i + 1))
        rel.append('<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>' % (len(names) + 1))
        wb.append("</sheets></workbook>")
        rel.append("</Relationships>")
        z.writestr("xl/workbook.xml", "".join(wb))
        z.writestr("xl/_rels/workbook.xml.rels", "".join(rel))
        z.writestr("xl/styles.xml", STYLES)
        for i, (_n, headers, rows) in enumerate(sheets):
            z.writestr("xl/worksheets/sheet%d.xml" % (i + 1), _sheet_xml(headers, rows))
    return buf.getvalue()
