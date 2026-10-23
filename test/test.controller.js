sap.ui.define (
  [
    './BaseController',
    'sap/ui/model/json/JSONModel',
    '../model/formatter',
    '../model/constant',
    'sap/ui/model/Filter',
    'sap/ui/model/FilterOperator',
    'sap/m/MessageBox',
    'sap/ui/core/Fragment',
    'sap/m/MessageToast',
  ],
  function (
    BaseController,
    JSONModel,
    formatter,
    constant,
    Filter,
    FilterOperator,
    MessageBox,
    Fragment,
    MessageToast
  ) {
    'use strict';
    return BaseController.extend ('namespace.test.controller.Worklist', {
      formatter: formatter,

      /**
         * Called when the worklist controller is instantiated.
         * @public
         */
      onInit: function () {
        var oViewModel;
        this._aTableSearchState = [];

        // Model used to manipulate control states
        oViewModel = new JSONModel ({
          worklistTableTitle: this.onGetText ('worklistTableTitle'),

          tableNoDataText: this.onGetText ('tableNoDataText'),
        });

        this.setModel (oViewModel, 'UI5LocalModel');

        this.setModel (new JSONModel (), 'Test1');
        this.setModel (new JSONModel (), 'MyTest');

        //? Modelo para anexos da criação
        this.getView ().setModel (
          new JSONModel ({
            attachments: [],
            dragOver: false,
          }),
          'AttachmentsModel'
        );
      },

      // END
    });
  }
);
