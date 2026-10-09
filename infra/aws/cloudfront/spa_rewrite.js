// Viewer-request: rotas do React (sem extensão) viram /index.html.
// Arquivos com extensão (js/css/png...) seguem para o S3 como estão.
function handler(event) {
  var request = event.request;
  var uri = request.uri;
  if (uri.endsWith('/')) {
    request.uri = '/index.html';
    return request;
  }
  var last = uri.split('/').pop();
  if (!last.includes('.')) {
    request.uri = '/index.html';
  }
  return request;
}
