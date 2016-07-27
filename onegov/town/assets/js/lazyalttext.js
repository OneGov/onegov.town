// append the alt text below the image in a span element
var appendAltText = function(image, alt) {
    image = $(image);
    var caption = null;

    image.attr('alt', alt);

    if (image.hasClass('missing-alt')) {
        caption = $("<span class='alt-text alt-text-missing'>").text(alt);
    } else {
        caption = $("<span class='alt-text'>").text(alt);
    }

    image.after(caption);
};

// load's onegov.file's alt texts through a separate HEAD request - leads
// to a higher server load (mtigated by caching), but it helps us to keep
// the alt text for all images in a single location, without having to
// do much on the html output side
var onLazyLoadAltText = function(element) {
    var target = $(element);
    var src = target.attr('src') || target.data('src');

    if (target.parents('.redactor-editor').length !== 0) {
        return;  // skip inside the redactor editor
    }

    if (target.parents('#redactor-image-manager-box').length !== 0) {
        return;  // skip inside the image manger selection box
    }

    if (target.siblings('.alt-text').length !== 0) {
        return;  // we already have an alt text
    }

    if (target.hasClass('.missing-alt')) {
        return;  // this alt text is not dynamic
    }

    $.ajax({method: 'HEAD', url: src,
        success: function(_data, _textStatus, request) {
            var alt = request.getResponseHeader('X-File-Note');

            if (alt.trim() !== "") {
                appendAltText(target, alt);
            }
        }
    });
};

$('.page-text img[alt][alt!=""], .missing-alt').each(function() {
    appendAltText(this, $(this).attr('alt'));
});

document.addEventListener('lazybeforeunveil', function(e) {
    onLazyLoadAltText(e.target);
});

$(document).ready(function() {
    $('.lazyload-alt').each(function() {
        onLazyLoadAltText(this);
    });
});
