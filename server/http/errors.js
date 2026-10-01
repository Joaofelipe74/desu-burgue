/** Erro com status HTTP e mensagem segura para mostrar ao usuário. */
export class HttpError extends Error {
  constructor(status, message, extra = {}) {
    super(message);
    this.status = status;
    this.publicMessage = message;
    this.extra = extra;
  }
}

export const badRequest = (msg, extra) => new HttpError(400, msg, extra);
export const unauthorized = (msg = 'Faça login para continuar.') => new HttpError(401, msg);
export const forbidden = (msg = 'Você não tem permissão para esta ação.') => new HttpError(403, msg);
export const notFound = (msg = 'Não encontrado.') => new HttpError(404, msg);
export const conflict = (msg, extra) => new HttpError(409, msg, extra);
