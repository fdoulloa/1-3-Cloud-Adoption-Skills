export type ToolParameter = {
  type: string;
  description: string;
  required?: boolean;
};

export type Tool = {
  name: string;
  description: string;
  parameters: Record<string, ToolParameter>;
  requires_confirmation?: boolean;
  execute: (args: any) => Promise<any>;
};

export type AgentRole = 'orchestrator' | 'business' | 'data' | 'code' | 'communication' | 'knowledge' | 'huaweicloud';

export interface A2AMessage {
  from: AgentRole;
  to: AgentRole;
  content: string;
  timestamp: Date;
}

export abstract class Agent {
  constructor(
    public id: string,
    public name: string,
    public role: AgentRole,
    public model: string,
    public description: string = '',
    public tools: Tool[] = []
  ) {}

  abstract think(messages: any[]): Promise<string>;

  /** Send a message to another agent via the Registry's A2A bus */
  async sendMessage(to: AgentRole, content: string): Promise<string> {
    const { registry } = await import('./Registry.js');
    const target = registry.getAgent(to);
    if (!target) throw new Error(`Agent ${to} not found for A2A message`);
    const msg: A2AMessage = { from: this.role, to, content, timestamp: new Date() };
    Audit.logA2A(this.role, to, content);
    const response = await target.think([
      { role: 'system', content: `[A2A Message from ${this.role}]: ${content}` }
    ]);
    return response;
  }
}

import { Audit } from './Audit.js';
