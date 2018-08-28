// adds functionality to the edit_list macro.
// Author: Johannes Mueller <j.mueller@reply.de>
function addItem(list, item) {
    // adds an item to the given list.
    // `list` some custom edit-list.
    // `item` some given item.
    var $list = $(list);
    var $proto = $list.find("li.proto");
    var $item = $proto.clone().removeClass("proto");
    var $itemText = $item.find(".item-text");
    var $itemDelete = $item.find(".item-delete");
    // already + 1 because of the proto item
    var index = $list.children("li").length;

    $item.attr("data-val", item);
    $item.attr("data-key", index);
    $itemText.html(item);
    $itemDelete.attr("data-target", item);
    $list.append($item);
}

function removeItem(list, item, key) {
    // removes an item from the given list.
    // `list` some custom edit-list.
    // `item` the item that should be removed.
    // `key` the key of the item that should be removed. At least one has to
    //  be given.
    var $list = $(list);
    if (key) {
        var $item = $list.find(`li[data-key='${key}']`);
        if (item && $item.data("val") != item) {
            return;
        }
        $item.remove();
    }

    if (item) {
        var $item = $list.find(`li[data-val='${item}']`);
        $item.remove();
    }

}

function clearList(list) {
    // empties the given list
    // `list` some custom edit-list.
    var $list = $(list);
    var $proto = $list.find(".proto");
    $list.empty();
    $list.append($proto);
}

function fillList(list, items) {
    // adds multiple items to the edit-list,
    // `list` a custom editable-list.
    // `items` an array of items.
    clearList(list);

    for (ind in items) {
        addItem(list, items[ind]);
    }
}

function removeItemEvent(event) {
    // removes an item from an item-list.
    // `event` refers to the originally triggered event.
    event.preventDefault();
    var $link = $(event.currentTarget);
    var $item = $link.parents("li.list-group-item");
    var $list = $link.parents("ul.list-group");
    var item = $item.data("val");
    var key = $item.data("key");
    // set disabled until the answer arrives
    removeItem($list[0], null, key);
    $(GLOBAL_OBJ).trigger("custom.edit-list.remove",
                          {list: $list[0], item: item});
}

function addItemEvent(event) {
    // adds an item to the item-list.
    // `event` refers to the originally triggered event.
    event.preventDefault();
    var $link = $(event.currentTarget);
    var $input = $link.prev("input[type='text']");
    var $list = $link.parents(".editable-list").children("ul.list-group");

    var items = $input.val().split(",").map(el => el.trim());
    $input.val("");
    for (ind in items) {
        addItem($list[0], items[ind]);
        $(GLOBAL_OBJ).trigger("custom.edit-list.add",
                            {list: $list[0], item: items[ind]});
    }
}

function itemInputEnter(event) {
    // checks the keyPress event and returns if enter wasn't triggered.
    // `event` refers to the keypress event.
    if (event.which != 13) return;
    $(event.currentTarget).next("a.item-add").click();
}

// use a delegated event on ul, in order to catch all the dynamically created
// items.
$(".editable-list ul").on("click", "li .item-delete", removeItemEvent);
$(".editable-list .item-add").click(addItemEvent);
$(".editable-list .item-input").keypress(itemInputEnter);