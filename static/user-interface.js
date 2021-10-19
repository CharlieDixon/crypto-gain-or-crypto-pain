function redirect(href) {
  window.location.href = href
}


function makeDefaultText() {
  $("div.text", "#c2b").addClass("default")
  $("div.text", "#c2b").html("Select coin to buy")
};
