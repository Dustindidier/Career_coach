"""Consistent, single-column application documents from the exact reviewed editor text."""
import io
import re
from html import escape


def blocks(text, kind='resume'):
    lines=text.splitlines()
    for index, raw in enumerate(lines):
        line=raw.strip()
        if not line:
            continue
        if index==0 and not re.match(r'\w+ \d{1,2}, \d{4}', line):
            style='name'
        elif kind=='resume' and line.isupper() and len(line)<95:
            style='heading'
        elif line.startswith(('• ', '- ')):
            style='bullet'
        elif kind=='resume' and (' | ' in line and not line.startswith(('BSN', 'Selected assignments:', 'Registered Nurse -')) and len(line)<130):
            style='job'
        elif line.startswith('Re:'):
            style='subject'
        elif kind=='coverLetter' and index < next((i for i,l in enumerate(lines) if l.startswith('Re:')),0) and not re.match(r'\w+ \d{1,2}, \d{4}',line):
            style='address'
        elif kind=='resume' and line.startswith('TARGET ROLE:'):
            style='target'
        else:
            style='body'
        yield style, line


def pdf(text, kind='resume'):
    from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_LEFT
    out=io.BytesIO()
    document=SimpleDocTemplate(out,pagesize=(612,792),rightMargin=48,leftMargin=48,
                              topMargin=43,bottomMargin=43,title='Resume' if kind=='resume' else 'Cover letter',author='')
    letter=kind=='coverLetter'
    normal=ParagraphStyle('body',fontName='Helvetica',fontSize=10.5 if letter else 10,
                          leading=14.5 if letter else 13,spaceAfter=10 if letter else 4,alignment=TA_LEFT)
    styles={'body':normal,
        'name':ParagraphStyle('name',parent=normal,fontName='Helvetica-Bold',fontSize=19,leading=23,spaceAfter=5,keepWithNext=True),
        'heading':ParagraphStyle('heading',parent=normal,fontName='Helvetica-Bold',fontSize=10,leading=13,spaceBefore=9,spaceAfter=5,keepWithNext=True),
        'job':ParagraphStyle('job',parent=normal,fontName='Helvetica-Bold',spaceAfter=3,keepWithNext=True),
        'subject':ParagraphStyle('subject',parent=normal,fontName='Helvetica-Bold',spaceBefore=5,spaceAfter=12,keepWithNext=True),
        'address':ParagraphStyle('address',parent=normal,spaceAfter=2,keepWithNext=True),
        'target':ParagraphStyle('target',parent=normal,fontName='Helvetica-Bold',spaceBefore=5,spaceAfter=7,keepWithNext=True),
        'bullet':ParagraphStyle('bullet',parent=normal,leftIndent=11,firstLineIndent=-8,spaceAfter=3)}
    story=[]
    for style,line in blocks(text,kind):
        if not letter and line=='PROFESSIONAL EXPERIENCE CONTINUED':
            story.append(PageBreak())
        line=line.replace('\u2011','-').replace('\u2013','-').replace('\u2014','-')
        story.append(Paragraph(escape(line),styles[style]))
    document.build(story)
    return out.getvalue()
