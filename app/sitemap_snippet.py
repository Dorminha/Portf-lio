
@app.get("/sitemap.xml", response_class=Response)
async def sitemap():
    """
    Gera o sitemap.xml para SEO.
    """
    content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://luandepaz.dev/</loc>
        <lastmod>{date}</lastmod>
        <changefreq>daily</changefreq>
        <priority>1.0</priority>
    </url>
    <url>
        <loc>https://luandepaz.dev/#projects</loc>
        <lastmod>{date}</lastmod>
        <changefreq>weekly</changefreq>
        <priority>0.8</priority>
    </url>
    <url>
        <loc>https://luandepaz.dev/#about</loc>
        <lastmod>{date}</lastmod>
        <changefreq>monthly</changefreq>
        <priority>0.5</priority>
    </url>
</urlset>
    """.format(date=datetime.now().strftime("%Y-%m-%d"))
    return Response(content=content, media_type="application/xml")
