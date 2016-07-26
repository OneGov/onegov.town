// load's onegov.file's alt texts through a separate HEAD request - leads
// to a higher server load (mtigated by caching), but it helps us to keep
// the alt text for all images in a single location, without having to
// do much on the html output side
document.addEventListener('lazybeforeunveil', function(e) {
    var src = $(e.target).data('src');

    $.ajax({method: 'HEAD', url: src,
        success: function(_data, _textStatus, request) {
            var alt = request.getResponseHeader('X-File-Note');

            if (alt.trim() !== "") {
                $(e.target).attr('alt', alt);
                $('<span>').text(alt).insertAfter(e.target);
            }
        }
    });
});
