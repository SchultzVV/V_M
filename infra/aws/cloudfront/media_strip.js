// Viewer-request: /media/<plataforma>/<arquivo> → /<plataforma>/<arquivo>
// (as imagens ficam num único bucket, com a plataforma como prefixo).
function handler(event) {
  var request = event.request;
  if (request.uri.startsWith('/media/')) {
    request.uri = request.uri.substring(6);
  }
  return request;
}
