import bleach


def sanitize_html(html):
    """ Takes the given html and strips all but a whitelisted number of tags
    from it.

    """

    if not html:
        return html

    allowed_tags = [
        'a',
        'abbr',
        'b',
        'br',
        'blockquote',
        'code',
        'div',
        'em',
        'i',
        'hr',
        'li',
        'ol',
        'p',
        'strong',
        'sup',
        'ul',
        'h1',
        'h2',
        'h3',
        'h4',
        'h5',
        'h6'
    ]

    return bleach.clean(html, tags=allowed_tags)