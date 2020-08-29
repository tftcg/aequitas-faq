
  function setup_autocomplete() {
      const site = 'https://faq.tf-rules.info/';
      // Grab the index json and pass the keys to jquery
      const url = `https://faq.tf-rules.info/faqindex.json`;
      fetch(url)
      .then((resp) => resp.json())
      .then(function(data) {
        $( "#search" ).autocomplete({
          source: Object.keys(data),
          select: function( event, ui ) {
            $(".ui-helper-hidden-accessible").hide();
            event.preventDefault();
            if(ui.item) {
                window.location.href = site + data[ui.item.value];
            } else {
                console.log("Nothing selected, input was " + ui.value );
            }
          }
        });
      })
      .catch(function(error) {
        console.log(error);
      });
  }

  function toggleSearch() {
      $( "#search" ).val('');
      $( "#search" ).toggle();
  }

  function toggleMenu() {
      $( "#menu" ).val('');
      $( "#menu" ).toggle();
  }

