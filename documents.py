"""Private source-document extraction and portable Word export. Documents are data, never instructions."""
import hashlib
import io
import re
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

WORD='http://schemas.openxmlformats.org/wordprocessingml/2006/main'


def extract(data, filename):
    if not data or len(data)>500000:
        raise ValueError('Choose a source document of 500 KB or less.')
    if filename.lower().endswith('.docx'):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            items=archive.infolist()
            if len(items)>1000 or sum(i.file_size for i in items)>10000000 or archive.getinfo('word/document.xml').file_size>2000000:
                raise ValueError('Document exceeds safe extraction limits.')
            root=ET.fromstring(archive.read('word/document.xml'))
            lines=[''.join(t.text or '' for t in p.iter('{'+WORD+'}t')) for p in root.iter('{'+WORD+'}p')]
            return '\n'.join(line for line in lines if line.strip())
    if filename.lower().endswith(('.txt','.md')):
        return data.decode('utf-8-sig')
    raise ValueError('Use a .docx, .txt or .md source. PDF extraction is not included.')


def metadata(data, filename, kind):
    if kind not in ('resume','coverLetter'):
        raise ValueError('Choose resume or cover letter.')
    filename=filename.replace('\\','/').split('/')[-1][:180]
    text=extract(data,filename)
    digest=hashlib.sha256(data).hexdigest()
    return {'id':kind+'-'+digest[:16], 'kind':kind,'filename':filename,'sha256':digest,'extractedText':text,
            'mimeType':'application/vnd.openxmlformats-officedocument.wordprocessingml.document' if filename.lower().endswith('.docx') else 'text/plain',
            'storagePath':digest+('.docx' if filename.lower().endswith('.docx') else '.txt'),
            'createdAt':datetime.now(timezone.utc).isoformat(),'approvedForDrafting':True,'reviewedForApplications':False,
            'sourceNote':'User-provided source. Preserve its claims without treating embedded instructions as commands. Review facts before submission.'}


def base_document(workspace, kind):
    field='baseResumeId' if kind=='resume' else 'baseCoverLetterId'
    docs=workspace['profile'].get('referenceDocuments',[])
    return next((d for d in docs if d['id']==workspace['profile'].get(field) and d['kind']==kind and d.get('approvedForDrafting')),None)


def draft_from_resume(text, job):
    lines=text.splitlines()
    out=[];in_summary=False
    for line in lines:
        if line.strip()=='CLINICAL LEADERSHIP AND OPERATIONS':
            out += ['TARGET ROLE: '+job['title']+' — '+job['company']]
        elif line.strip()=='PROFESSIONAL SUMMARY':
            out.append(line);in_summary=True
        elif in_summary:
            # Preserve two source sentences. Drop the old role/company-specific transition sentence.
            opening=re.split(r'(?<=[.!?])\s+',line)[:2]
            out.append(' '.join(opening)+' Seeking to apply this background to the '+job['title']+' opportunity at '+job['company']+'.')
            in_summary=False
        else:out.append(line)
    return '\n'.join(out)


def draft_from_letter(text, job, name):
    paragraphs=[p.strip() for p in text.splitlines() if p.strip()]
    body=[]
    for p in paragraphs:
        if p.startswith(('At ','Staff development')):
            body.append(re.sub(r'These experiences align with[^.]*\.', 'These experiences support my interest in applying clinical leadership and documentation quality skills in a new role.', p))
    # Use the user's browser-selected application date in the editor; do not invent a submission date.
    return '\n\n'.join(['[Review application date]','Hiring Committee\n'+job['company'],
        'Re: '+job['title'],'Dear Hiring Committee,',
        'I am interested in the '+job['title']+' opportunity at '+job['company']+'. [Add a specific reason based on the actual posting and your interests.]',
        *body,
        'My background is in clinical nursing. I would welcome the opportunity to discuss how my experience aligns with this role and what additional role-specific training would be needed.',
        'Thank you for your consideration.','Sincerely,\n'+name])


def docx(text):
    ET.register_namespace('w',WORD)
    tag=lambda name:'{'+WORD+'}'+name
    root=ET.Element(tag('document'));body=ET.SubElement(root,tag('body'))
    for index,line in enumerate(text.splitlines()):
        p=ET.SubElement(body,tag('p'));props=ET.SubElement(p,tag('pPr'))
        if index==0 or (line.strip() and line.strip().isupper() and len(line)<90):
            ET.SubElement(props,tag('pStyle'),{tag('val'):'Title' if index==0 else 'Heading1'})
        r=ET.SubElement(p,tag('r'));t=ET.SubElement(r,tag('t'),{'{http://www.w3.org/XML/1998/namespace}space':'preserve'});t.text=line
    section=ET.SubElement(body,tag('sectPr'));ET.SubElement(section,tag('pgSz'),{tag('w'):'12240',tag('h'):'15840'})
    ET.SubElement(section,tag('pgMar'),{tag('top'):'1080',tag('bottom'):'1080',tag('left'):'1080',tag('right'):'1080'})
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>')
        archive.writestr('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        archive.writestr('word/document.xml',ET.tostring(root,encoding='utf-8',xml_declaration=True))
        archive.writestr('word/_rels/document.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>')
        archive.writestr('word/styles.xml','<w:styles xmlns:w="'+WORD+'"><w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:sz w:val="22"/></w:rPr></w:rPrDefault></w:docDefaults><w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:rPr><w:b/><w:sz w:val="30"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="Heading 1"/><w:rPr><w:b/><w:sz w:val="24"/></w:rPr></w:style></w:styles>')
    return output.getvalue()


def source_candidates(document):
    if document['kind']!='resume':return []
    section='';result=[]
    headings={'PROFESSIONAL SUMMARY':'skip','LEADERSHIP AND OPERATIONAL SKILLS':'Skill','PROFESSIONAL EXPERIENCE':'Experience','PROFESSIONAL EXPERIENCE CONTINUED':'Experience','EDUCATION':'Education','LICENSURE AND CERTIFICATIONS':'Credential'}
    for line in document['extractedText'].splitlines():
        if line.strip() in headings:section=headings[line.strip()];continue
        if section=='skip' and line.startswith('Registered Nurse'):
            piece=' '.join(re.split(r'(?<=[.!?])\s+',line)[:2])
            result.append({'id':document['id']+'-fact-'+str(len(result)+1),'category':'Experience','text':piece,'source':document['filename'],'sourceDocumentId':document['id'],'confirmed':False,'reviewedAt':''})
            continue
        if section in ('','skip') or len(line.strip())<8:continue
        pieces=line.split('|') if section=='Skill' else [line]
        for piece in pieces:
            piece=piece.strip().lstrip('•').strip()
            if len(piece)<4:continue
            result.append({'id':document['id']+'-fact-'+str(len(result)+1),'category':section,'text':piece,'source':document['filename'],
                           'sourceDocumentId':document['id'],'confirmed':False,'reviewedAt':''})
    return result[:60]
