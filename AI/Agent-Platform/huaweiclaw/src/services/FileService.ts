import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const { PDFParse } = require('pdf-parse');
const mammoth = require('mammoth');
import * as xlsx from 'xlsx';

export class FileService {
  static async parseFile(buffer: Buffer, mimetype: string): Promise<string> {
    if (mimetype === 'application/pdf') {
      return this.parsePdf(buffer);
    } else if (
      mimetype === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' ||
      mimetype === 'application/msword'
    ) {
      return this.parseWord(buffer);
    } else if (
      mimetype === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' ||
      mimetype === 'application/vnd.ms-excel'
    ) {
      return this.parseExcel(buffer);
    } else {
      throw new Error(`Unsupported file type: ${mimetype}`);
    }
  }

  private static async parsePdf(buffer: Buffer): Promise<string> {
    try {
      const pdf = new PDFParse({ data: buffer });
      const result = await pdf.getText();
      return result.text;
    } catch (error) {
      console.error('Error parsing PDF:', error);
      throw new Error('Failed to parse PDF file');
    }
  }

  private static async parseWord(buffer: Buffer): Promise<string> {
    try {
      const result = await mammoth.extractRawText({ buffer });
      return result.value;
    } catch (error) {
      console.error('Error parsing Word:', error);
      throw new Error('Failed to parse Word file');
    }
  }

  private static async parseExcel(buffer: Buffer): Promise<string> {
    try {
      const workbook = xlsx.read(buffer, { type: 'buffer' });
      let text = '';
      workbook.SheetNames.forEach((sheetName) => {
        const sheet = workbook.Sheets[sheetName];
        text += `Sheet: ${sheetName}\n`;
        text += xlsx.utils.sheet_to_csv(sheet);
        text += '\n\n';
      });
      return text;
    } catch (error) {
      console.error('Error parsing Excel:', error);
      throw new Error('Failed to parse Excel file');
    }
  }
}
