/* assignment.js
**
*/

function authenticateAjax() {
    // Sets up authentication for AJAX transactions
    var csrftoken = Cookie.get('csrftoken');
    function csrfSafeMethod(method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });
}

//import modal from './modal';
//import showdown from 'showdown';

/* modal.js
**
** Pops a modal dialog up on screen.
*/

function modal(nextSelector) {
    var overlay = '#modal-overlay';
    $(overlay).addClass('visible');
    $(nextSelector).addClass('visible');
    $(overlay).click(function(){
        $(overlay).removeClass('visible');
        $(nextSelector).removeClass('visible');
    });
    $('.close-modal').click(function(){
        $(overlay).removeClass('visible');
        $(nextSelector).removeClass('visible');
    });
}

// https://github.com/kevinchappell/formBuilder/issues/787
function setOptionValue(evt) {
  evt.target.nextSibling.value = evt.target.value;
}

function applyOptionChanges(option) {
  option.removeEventListener("input", setOptionValue, false);
  option.addEventListener("input", setOptionValue, false);
  option.nextSibling.style.display = "none";
}

function selectOptions(fld) {
  const optionLabelInputs = fld.querySelectorAll(".option-label");
  for (var i = 0; i < optionLabelInputs.length; i++) {
    applyOptionChanges(optionLabelInputs[i]);
  }
}

function createObserver(fld) {
  const callback = function() {
    selectOptions(fld);
  };
  const observer = new MutationObserver(callback);
  observer.observe(fld.querySelector(".sortable-options"), { childList: true });
  return observer;
}

function onAddOptionInput(fld) {
  selectOptions(fld);
  createObserver(fld);
}

$(document).ready(function(){
  var formBuilder = $("#build-wrap").formBuilder({
      disableFields: [
        'autocomplete',
        'button',
        'file',
        'hidden',
        'radio-group'
      ],
      disabledAttrs: [
        'access',
        'className',
        'inline',
        'maxlength',
        'multiple',
        'other',
        'placeholder',
        'rows',
        'step',
        'style',
        'subtype',
        'toggle',
        'value'
      ],
      typeUserAttrs: {
        "checkbox-group": {
          gallery: {
            label: "Gallery",
            type: "checkbox"
          }
        },
        checkbox2: {
          gallery: {
            label: "Gallery",
            type: "checkbox"
          }
        },
        date: {
          gallery: {
            label: "Gallery",
            type: "checkbox"
          }
        },
        number: {
          gallery: {
            label: "Gallery",
            type: "checkbox"
          }
        },
        select: {
          gallery: {
            label: "Gallery",
            type: "checkbox"
          }
        },
        text: {
          gallery: {
            label: "Gallery",
            type: "checkbox"
          }
        },
        textarea: {
          gallery: {
            label: "Gallery",
            type: "checkbox"
          }
        },
        header: {
          name: {
            label: "Name"
          }
        },
        paragraph: {
          name: {
            label: "Name"
          }
        }
      },
      typeUserEvents: {
        "checkbox-group": {
          onadd: onAddOptionInput
        },
        "radio-group": {
          onadd: onAddOptionInput
        },
        select: {
          onadd: onAddOptionInput
        }
      },
      disabledActionButtons: ['data', 'save', 'clear'],
      fields: [{label: 'Check Box', attrs: {type: 'checkbox2'}, icon: ''}],
      templates: {checkbox2: function(data) {
        return {
          field: '<input type="checkbox" id="' + data.name + '">'
        };
      }},
    defaultFields: JSON.parse($("#id_assignment-form_json").length ? $("#id_assignment-form_json").val() : "[]")
  });

  formBuilder.promise.then(function() {
    $("#build-wrap .fld-gallery").each(function() {
      $(this).prop("checked", $(this).val() === "true");
    });
  });


  $("form.create-assignment").submit(function() {
    $("#id_assignment-form_json").val(formBuilder.actions.getData('json'));
  });

  $("#add-assignment-data").click(function(e) {
    e.preventDefault();
    cloneMore("div.assignment-data:last");
  });

  $("#message-modal form").submit(function(e) {
    e.preventDefault();
    var mailLink = $("a.message-link[data-response='" + $("#id_response").val() + "']");
    $.ajax({
      url: '/assignments/message/',
      type: 'post',
      data: $(this).serialize(),
      success: function() {
        mailLink.removeClass('failure');
        mailLink.addClass('success');
      },
      error: function() {
        mailLink.removeClass('success');
        mailLink.addClass('failure');
      }
    });
  });

  function cloneMore(selector) {
    var newElement = $(selector).clone(true);
    var total = $('#id_data-TOTAL_FORMS').val();
    newElement.find(':input').each(function() {
      var name = $(this).attr('name').replace('-' + (total-1) + '-','-' + total + '-');
      var id = 'id_' + name;
      $(this).attr({'name': name, 'id': id}).val('').removeAttr('checked');
    });
    newElement.find('label').each(function() {
      var newFor = $(this).attr('for').replace('-' + (total-1) + '-','-' + total + '-');
      $(this).attr('for', newFor);
    });
    total++;
    $('#id_data-TOTAL_FORMS').val(total);
    $(selector).after(newElement);
  }

  const params = new URLSearchParams(window.location.search);
  var
    page = 1,
    pageSize = 10,
    lastPage = 1,
    flag = params.get("flag") || null,
    search = params.get("search") || "";

  function handleUpdateResponses(data) {
    var response, values, dataValues, dataUrlP, oEmbed, flagged, galleried,
      tags, dataSection, mailLink, editAccess;
    var responses = $("section.assignment-responses");
    responses.html("");
    var pencil = $("#pencil-svg").html();
    var mail = $("#email-svg").html();
    var converter = new showdown.Converter();

    // generate the responses
    for(var i = 0; i < data.results.length; i++) {
      response = $("<section>").addClass("textbox assignment-response collapsable");
      if (data.results[i].data) {
        dataUrlP = `<p>Data:
          <a href="${data.results[i].data}">${data.results[i].data}</a>
          </p>`;
        oEmbed = `<div class="embed" data-url="${data.results[i].data}"></div>`;
      } else {
        dataUrlP = "";
        oEmbed = "";
      }
      editAccess = data.results[i].flag !== undefined;
      if (editAccess) {
        flagged = data.results[i].flag ? "checked" : "";
        galleried = data.results[i].gallery ? "checked" : "";
        tags = data.results[i].tags ? data.results[i].tags.join(', ') : '';
        if (data.results[i].user) {
          mailLink = `<a href="#" class="message-link" data-response="${data.results[i].id}" data-name="${data.results[i].user}">${mail}</a>`;
        } else {
          mailLink = "";
        }
        response.append(`
          <header class="textbox__header">
            <p class="from nocollapse">
              <a href="/assignments/${data.results[i].id}/edit/" class="edit-link">
                ${pencil}
              </a>
              ${mailLink}
              From: ${data.results[i].user || data.results[i].ip_address || 'Anonymous'}
            </p>
            ${dataUrlP}
            <time class="date">
              ${data.results[i].datetime}
            </time>
          </header>
          <section class="textbox__section actionables">
            <label>
              Flagged:
              <input type="checkbox" class="flag-checkbox" data-assignment="${data.results[i].id}" ${flagged}>
            </label>
            <label>
              Gallery:
              <input type="checkbox" class="gallery-checkbox" data-assignment="${data.results[i].id}" ${galleried}>
            </label>
            <label>
              Tags:
              <input type="text" class="tag-box" data-assignment="${data.results[i].id}" value="${tags}">
            </label>
          </section>`);
      } else {
        response.append(`
          <header class="textbox__header">
            <p class="from nocollapse">
              From: ${data.results[i].user || data.results[i].ip_address || 'Anonymous'}
            </p>
            ${dataUrlP}
            <time class="date">
              ${data.results[i].datetime}
            </time>
          </header>`);
      }
      values = $("<dl>");
      dataValues = data.results[i].values;
      for (var j = 0; j < dataValues.length; j++) {
        values.append("<dt>" + dataValues[j].field + "</dt>");
        values.append("<dd>" + converter.makeHtml(dataValues[j].value) + "</dd>");
      }
      dataSection = $("<section>").addClass("textbox__section").html(values);
      response.append(dataSection);
      if (data.results[i].edit_user) {
        dataSection.append($("<p>").html(
          `<em>This submission was edited by ${data.results[i].edit_user} at
          ${data.results[i].edit_datetime}.` +
          (editAccess ? `<a href="/assignments/${data.results[i].id}/revert">
            View the original submission and, if necessary, revert.
          </a>` : '') +
          `</em>`
        ));
      }
      response.append(oEmbed);
      responses.append(response);
    }
    // Need to re-run these so they apply to dynamically created content
    $('.collapsable header').click(function(){
      $(this).parent().toggleClass('collapsed');
    });
    $('.collapsable header').find('.nocollapse').click(function(event){
      // Prevent click from propagating up to the collapsable header.
      event.stopPropagation();
    });
    $('.flag-checkbox').change(function(){
      $.ajax({
        url: "/api/assignment-responses/" + $(this).data("assignment") + "/",
        type: "PATCH",
        data: {
          'flag': $(this).prop("checked")
        }
      });
    });
    $('.gallery-checkbox').change(function(){
      $.ajax({
        url: "/api/assignment-responses/" + $(this).data("assignment") + "/",
        type: "PATCH",
        data: {
          'gallery': $(this).prop("checked")
        }
      });
    });
    $('.flag-all').click(function(){
      $('.flag-checkbox').prop('checked', $(this).prop('checked')).change();
    });
    $('.gallery-all').click(function(){
      $('.gallery-checkbox').prop('checked', $(this).prop('checked')).change();
    });
    $('.message-link').click(function(e){
      e.preventDefault();
      $('#id_response').val($(this).data('response'));
      $('#message-modal .name').text($(this).data('name'));
      modal($('#message-modal'));
      return false;
    });
    if ($("#data-inline").prop("checked")) {
      $(".embed").each(function(){
        var embed = $(this);
        $.ajax({
          url: "/assignments/oembed/",
          type: "GET",
          data: {"url": $(this).data('url')},
          success: function(data) {
            embed.html(data);
          }
        });
      });
    }

    var tagTimeoutIds = {};
    function tagHandler() {
      var assignment = $(this).data("assignment");
      var tags = $(this).val();
      clearTimeout(tagTimeoutIds[assignment]);
      tagTimeoutIds[assignment] = setTimeout(function() {
        // Runs 1 second (1000 ms) after the last change
        $.ajax({
          url: "/api/assignment-responses/" + assignment + "/",
          type: "PATCH",
          data: {'tags': tags}
        });
      }, 1000);
    }
    $(".tag-box").on("input propertychange change", tagHandler);

    // update the pagination bar
    $("#assignment-responses .pagination__control__item .first").text(
      ((page - 1) * pageSize) + 1
    );
    $("#assignment-responses .pagination__control__item .last").text(
      Math.min(((page - 1) * pageSize) + pageSize, data.count)
    );
    $("#assignment-responses .pagination__control__item .total").text(
      data.count
    );
    lastPage = Math.ceil(data.count / pageSize);
    $("#assignment-responses .pagination__control__item .total-pages").text(
      lastPage
    );
    var select = $("#assignment-responses .pagination__control__item #page");
    select.html("");
    for (i = 1; i <= lastPage; i++) {
      select.append($("<option value='" + i + "'>" + i + "</option>"));
    }
    select.val(page);
    if (data.next) {
      $("#assignment-responses .pagination__links .next")
        .addClass("more").removeClass("no-more");
    } else {
      $("#assignment-responses .pagination__links .next")
        .addClass("no-more").removeClass("more");
    }
    if (data.previous) {
      $("#assignment-responses .pagination__links .previous")
        .addClass("more").removeClass("no-more");
    } else {
      $("#assignment-responses .pagination__links .previous")
        .addClass("no-more").removeClass("more");
    }

  }

  $("#data-inline").change(function() {
    if ($(this).prop("checked")) {
      $(".embed").each(function(){
        var embed = $(this);
        $.ajax({
          url: "/assignments/oembed/",
          type: "GET",
          data: {"url": $(this).data('url')},
          success: function(data) {
            embed.html(data);
          }
        });
      });
    }
  });

  function updateResponses() {
    if (window.location.hash == "#assignment-responses") {
      history.pushState(
        '',
        document.title,
        `?flag=${flag}&search=${search}#assignment-responses`
      );
    }
    $.ajax({
      url: "/api/assignment-responses/",
      type: 'GET',
      data: {
        'assignment': $("section.assignment-responses").data("assignment"),
        'page_size': pageSize,
        'page': page,
        'flag': flag,
        'search': search
      },
      success: handleUpdateResponses
    });
  }

  if ($("section.assignment-responses").length) {
    updateResponses();
  }

  $("#assignment-responses .pagination__links .first-page").click(function(e) {
    e.preventDefault();
    page = 1;
    updateResponses();
  });
  $("#assignment-responses .pagination__links .previous-page").click(function(e) {
    e.preventDefault();
    page = Math.max(page - 1, 1);
    updateResponses();
  });
  $("#assignment-responses .pagination__links .next-page").click(function(e) {
    e.preventDefault();
    page = Math.min(page + 1, lastPage);
    updateResponses();
  });
  $("#assignment-responses .pagination__links .last-page").click(function(e) {
    e.preventDefault();
    page = lastPage;
    updateResponses();
  });
  $("#assignment-responses .pagination #page").change(function() {
    var newPage = parseInt($(this).val());
    if (isNaN(newPage)) {
      page = 1;
    } else if (newPage < 1) {
      page = 1;
    } else if (newPage > lastPage) {
      page = lastPage;
    } else {
      page = newPage;
    }
    updateResponses();
  });
  $("#assignment-responses .pagination #per-page").change(function() {
    var newPageSize = parseInt($(this).val());
    if (isNaN(newPageSize)) {
      pageSize = 10;
    } else if (newPageSize < 10) {
      pageSize = 10;
    } else if (newPageSize > 50) {
      pageSize = 50;
    } else {
      pageSize = newPageSize;
    }
    page = 1;
    updateResponses();
  });
  $("#assignment-responses #filter").change(function() {
    var newFlag = $(this).val();
    if (newFlag === "flag") {
      flag = true;
    } else if (newFlag === "no-flag") {
      flag = false;
    } else {
      flag = null;
    }
    updateResponses();
  });

  var timeoutId;
  function searchHandler() {
    search = $(this).val();
    clearTimeout(timeoutId);
    timeoutId = setTimeout(function() {
      // Runs 1 second (1000 ms) after the last change
      updateResponses();
    }, 1000);
  }
  $("#assignment-responses #assignment-search").on(
    "input propertychange change", searchHandler);

  authenticateAjax();
});

/* tabs.js
**
** Tabbed-based navigation using Javascript
** and the manipulation of URL hashes.
**
** Turn classed anchor links into tabs,
** and allow elements within those tabs to
** be accessible by hash as well.
*/

var tabs = $('.tab').attr('tabindex', '0');         // collect all the tabs and set tabindex to 0
var tabTargets = tabs.map(function() {              // get an array of tab-panel ids
  return this.hash;
}).get();
var tabPanels = $(tabTargets.join(','));            // use those ids to get the actual tab-panels

function showTab(hash) {
  // remove the active class from the tabs,
  // and add it back to the one the user selected
  tabs.removeClass('active').attr('aria-selected', 'false').filter(function() {
    return (this.hash === hash);
  }).addClass('active').attr('aria-selected', 'true');
  // hide all the panels, then filter to the one
  // we're interested in and show it
  tabPanels.find('.tab-panel-heading').hide();
  tabPanels.hide().attr('aria-hidden', 'true').filter(hash).show().attr('aria-hidden', 'false');
}

function handleHashChange() {
  // Check if the hash is a target.
  // If there's no hash, show the first tab.
  var hash = location.hash;
  hash = !hash ? tabTargets[0] : hash;
  // If there's no tabs to show, just return.
  if (!hash) {
    return;
  }
  if (tabTargets.includes(hash)) {
    showTab(hash);
    return;
  }
  // check if the hash is a child of a target
  // if it is, switch to that tab and stop checking
  $(tabTargets).each(function(_, target) {
    if ($(hash).closest(target).length > 0) {
      showTab(target);
      // scroll to the hashed item
      var elementOffset = $(hash).offset();
      // we subtract (42+19) due to the fixed header height and some spacing
      window.scrollTo(elementOffset.left, elementOffset.top - (42+19));
      // return false to prevent any other tabs from being matched
      return false;
    }
  });
}

// Bind to hashchange event
$(window).on('hashchange', handleHashChange);

// Initialize
handleHashChange();

