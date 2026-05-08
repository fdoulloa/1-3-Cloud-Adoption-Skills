import { Agent, AgentRole } from './Agent.js';

export class Registry {
  private agents: Map<string, Agent> = new Map();

  register(agent: Agent) {
    this.agents.set(agent.role, agent);
  }

  getAgent(role: AgentRole): Agent | undefined {
    return this.agents.get(role);
  }

  getAllAgents(): Agent[] {
    return Array.from(this.agents.values());
  }
}

export const registry = new Registry();
