import winston from 'winston';

export const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: 'audit.log' })
  ]
});

export class Audit {
  static logToolCall(agentId: string, toolName: string, params: any) {
    logger.info('Tool Call', {
      type: 'tool_call',
      agentId,
      toolName,
      params,
      timestamp: new Date().toISOString()
    });
  }

  static logSecurityEvent(event: string, details: any) {
    logger.warn('Security Event', {
      type: 'security_event',
      event,
      details,
      timestamp: new Date().toISOString()
    });
  }

  static logA2A(from: string, to: string, content: string) {
    logger.info('A2A Message', {
      type: 'a2a',
      from,
      to,
      content: content.substring(0, 200),
      timestamp: new Date().toISOString()
    });
  }
}
