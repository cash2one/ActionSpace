function copyToClipboard(id) {
  var $temp = $("<textarea>");
  $("body").append($temp);
  $temp.val($(document.getElementById(id)).text()).select();
  document.execCommand("copy");
  $temp.remove();
}
