import io
import unittest
import zipfile
from pypdf import PdfReader
from documents import docx, extract
from material_exports import pdf


class ExportTests(unittest.TestCase):
    def test_pdf_preserves_literal_text_and_complete_history(self):
        text='Candidate Name\nPROFESSIONAL EXPERIENCE\nHospital | 2020 - 2026\n• Reviewed <records> & escalated concerns.\nPROFESSIONAL EXPERIENCE CONTINUED\nEarlier hospital | 2015 - 2020\nEDUCATION\nGraduate coursework; degree not completed.'
        reader=PdfReader(io.BytesIO(pdf(text)))
        self.assertEqual(len(reader.pages),2)
        result='\n'.join(p.extract_text() for p in reader.pages)
        for part in ('<records> & escalated','Earlier hospital','degree not completed'):
            self.assertIn(part,result)

    def test_cover_letter_stays_one_page_and_keeps_signature(self):
        text='Candidate Name\nBSN, RN | Ohio\nOctober 26, 2026\nHiring Committee\nExample\nRe: Clinical Research Nurse\nDear Hiring Committee,\n'+'\n'.join(['Clinical experience and documentation. '*14]*4)+'\nSincerely,\nCandidate Name, BSN, RN'
        reader=PdfReader(io.BytesIO(pdf(text,'coverLetter')))
        self.assertEqual(len(reader.pages),1)
        self.assertIn('Candidate Name, BSN, RN',reader.pages[0].extract_text())

    def test_word_keeps_literal_claims_and_page_controls(self):
        text='Candidate Name\nPROFESSIONAL EXPERIENCE\nHospital | 2015 - 2026\n• Clinical work\nPROFESSIONAL EXPERIENCE CONTINUED\nGraduate coursework; degree not completed.'
        raw=docx(text)
        self.assertEqual(extract(raw,'resume.docx'),text)
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            xml=z.read('word/document.xml')
            self.assertIn(b'pageBreakBefore',xml)
            self.assertIn(b'keepNext',xml)
