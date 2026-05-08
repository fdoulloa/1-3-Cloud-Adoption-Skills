import fs from 'fs';
import path from 'path';

export interface Skill {
  name: string;
  description: string;
  content: string;
}

export class SkillService {
  private skillsPath: string;

  constructor() {
    this.skillsPath = path.join(process.cwd(), 'src', 'mcp', 'skills', 'superpowers', 'skills');
  }

  async listSkills(): Promise<string[]> {
    try {
      if (!fs.existsSync(this.skillsPath)) return [];
      const dirs = fs.readdirSync(this.skillsPath, { withFileTypes: true });
      return dirs.filter(d => d.isDirectory()).map(d => d.name);
    } catch (e) {
      console.error('SkillService: Error listing skills:', e);
      return [];
    }
  }

  async getSkill(name: string): Promise<Skill | null> {
    try {
      if (!name) {
        console.error('SkillService: getSkill called with undefined or empty name.');
        return null;
      }
      const skillFile = path.join(this.skillsPath, name, 'SKILL.md');
      if (!fs.existsSync(skillFile)) return null;

      const content = fs.readFileSync(skillFile, 'utf-8');
      
      // Simple extraction of description from the first few lines
      const descMatch = content.match(/description:\s*(.*)/);
      const description = descMatch ? descMatch[1] : `Skill for ${name}`;

      return {
        name,
        description,
        content
      };
    } catch (e) {
      console.error(`SkillService: Error reading skill ${name}:`, e);
      return null;
    }
  }
}
