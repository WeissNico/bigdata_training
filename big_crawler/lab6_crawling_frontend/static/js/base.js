// Adds some custom functionality to the base.html layout, which is available
// in all views.
// Author: Johannes Mueller <j.mueller@reply.de>
var STATUS_MAPPING = {"": {text: "", color: "secondary"},
                      "open": {text: "UNREAD", color: "danger", rank: 0},
                      "waiting": {text: "ON HOLD", color: "warning", rank: 1},
                      "finished": {text: "ASSIGNED", color: "success", rank: 2}
                     };

// global object for global event registration
var GLOBAL_OBJ = {};

function toTitleCase(str) {
    // Changes a snake- or kebab-case word into a title-cased sentence.
    // `str` is a snake- or kebab-case word.
    // EXAMPLES: 
    //  toTitleCase("next_run")  // => "Next Run"
    //  toTitleCase("this-is-not-helpful")  // => "This Is Not Helpful"
    var words = str.split(/[_-]/);
    return words.map(word => {
        if (word.length == 0) {
            return word
        }
        return word[0].toUpperCase() + word.slice(1);
    }).join(" ")
}

function omap(obj, func) {
    // Maps a function over the values of an object.
    return Object.keys(obj).reduce((acc, key) => {
        acc[key] = func(obj[key]);
        return acc
    }, {});
}

function deepcopy(element) {
    // Creates a deep copy of an object. Quite naïve.
    if (Array.isArray(element)) {
        return element.map(deepcopy)
    }
    else if (element !== null && typeof(element) === 'object') {
        return omap(element, deepcopy)
    }
    return element
}

function flipIcon(event){
    // changes the caret of the cat-links according to the expansion of the
    // referenced div.
    // `event` describes the input-event
    // EXPECTS THE CLASSES (as an array of length 2) BOUND TO `this`
    var $btn = $(event.currentTarget);
    var $collapse;
    if ($btn.is("a")) {
        $collapse = $($btn.prop("hash"));
    }
    else if ($btn.is("button")) {
        $collapse = $($btn.data("target"));
    }
    var $icon = $btn.find(".fas");
    var toggled = $collapse.hasClass("show");
    $icon.toggleClass(this[0], toggled);
    $icon.toggleClass(this[1], !toggled);
}

function accumulateJobs(event) {
    // accumulates all the open jobs of a month and updates the display-badges.
    // `event` describes the originally triggered event, its target describes
    //      the month, which the jobs should be accumulated for.
    var $monthDiv = $(event.target);
    var $monthLink = $monthDiv.prev(".nav-item");
    var sums = {"open": 0, "waiting": 0, "finished": 0};
    $monthDiv.children(".nav-item").each(function() {
        $(this).find(".badge.indicator").children(".data-span")
         .each(function() {
            sums[$(this).data("var")] += parseInt($(this).text())
        });
    });
    $monthLink.find(".data-span").each(function() {
        $(this).html(sums[$(this).data("var")]);
    });
    $monthLink.find(".badge.indicator").trigger("custom.change.badges");
}

function changeIndicatorColors(event) {
    // changes the color of the given indicator.
    // `element` refers to an indicator badge (.badge.indicator)
    var $badge = $(event.target);
    var $dataSpans = $badge.find(".data-span");
    var classes = Object.values(STATUS_MAPPING).map(el => `badge-${el.color}`)
                                               .join(" ");
    var values = $dataSpans.map(function(_, el) {
        return {
            type: $(el).data("var"),
            number: $(el).text()
        };
    }).get();
    var mode = values.reduce(function(acc, val) {
        // continue, when there are 0 occurences
        if (val.number == 0) return acc;
        if (STATUS_MAPPING[val.type].rank < STATUS_MAPPING[acc].rank) {
            acc = val.type;
        }
        return acc;
    }, "finished");
    var mapping = STATUS_MAPPING[mode];
    $badge.removeClass(classes).addClass(`badge-${mapping.color}`);
}

function smoothScrollToTop(event) {
    var position = $("#topAnchor").offset().top;
    $("html").animate({scrollTop: position}, "1000");
    event.preventDefault();
}

function jsonPost(url, data, callback) {
    // sends data to an url using the json format.
    // `url` the url to access.
    // `data` an object that will be JSON serialized.
    // `callback` the function that should be called after submission.
    $.ajax({
        url: url,
        type: "POST",
        contentType: "application/json",
        data: JSON.stringify(data)
    }).done(callback);
}

function $$(query, context) {
    // A custom selector for querySelectorAll
    return Array.prototype.slice.call(
        (context || document).querySelectorAll(query)
    );
}

function findComponents() {
    // Finds the mount points for the components in a page and updates them
    // accoringly.
    var elements = $$("[data-component]");
    elements.forEach(function(el) {
        // retrieve the component by name
        const component = window[el.getAttribute("data-component")] || CheckList;
        var attributes = {};
        // parse all attributes as JSON strings.
        for (var attr in el.dataset) {
            try {
                attributes[attr] = JSON.parse(el.dataset[attr]);
            }
            catch (e) {
                // catch the json parse errors and assign the string instead
                attributes[attr] = el.dataset[attr]
            }
        }
        attributes.element = el;
        
        m.mount(el, {view: function () {return m(component, attributes)}});
    });
}

$(".badge.indicator").on("custom.change.badges", changeIndicatorColors);
$(".category").on("custom.change.badges", accumulateJobs);
$(".cat-link").click(flipIcon.bind(["fa-caret-right", "fa-caret-down"]));
$(".btn-controls").click(flipIcon.bind(["fa-angle-double-up",
                                        "fa-angle-double-down"]));
$(".btn-top").click(smoothScrollToTop);

$(".badge.indicator").trigger("custom.change.badges");
$(".category").trigger("custom.change.badges");