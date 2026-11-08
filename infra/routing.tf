# CloudFront only serves index.html at the root. This tiny function does the same for every folder:
#   /briefing/  →  /briefing/index.html
#   /briefing   →  301 to /briefing/ (so relative links keep working)
resource "aws_cloudfront_function" "pretty_urls" {
  name    = "nzoyamarques-pretty-urls"
  runtime = "cloudfront-js-2.0"
  comment = "Serve index.html for folder paths"
  publish = true
  code    = <<-EOT
    function handler(event) {
      var request = event.request;
      var uri = request.uri;
      if (uri.endsWith('/')) {
        request.uri = uri + 'index.html';
        return request;
      }
      var last = uri.split('/').pop();
      if (last.indexOf('.') === -1) {
        return {
          statusCode: 301,
          statusDescription: 'Moved Permanently',
          headers: { location: { value: uri + '/' } }
        };
      }
      return request;
    }
  EOT
}
