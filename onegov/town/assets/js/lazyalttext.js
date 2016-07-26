// load's onegov.file's alt texts through a separate HEAD request - leads
// to a higher server load (mtigated by caching), but it helps us to keep
// the alt text for all images in a single location, without having to
// do much on the html output side
document.addEventListener('lazybeforeunveil', function(e) {
    var target = $(e.target);
    var src = target.data('src');

    if (target.parents('.redactor-editor').length !== 0) {
        return;  // skip inside the redactor editor
    }

    if (target.parents('#redactor-image-manager-box').length !== 0) {
        return;  // skip inside the image manger selection box
    }

    $.ajax({method: 'HEAD', url: src,
        success: function(_data, _textStatus, request) {
            var alt = request.getResponseHeader('X-File-Note');

            if (alt.trim() !== "") {
                $(e.target).attr('alt', alt);
                $('<span class="alt-text">').text(alt).insertAfter(e.target);
            }
        }
    });
});
