# -*- coding: utf-8 -*-
import os
import datetime as dt

import numpy as np
import pandas as pd
from PyQt5.QtCore import pyqtSlot, Qt
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QDialog, QMessageBox, QInputDialog, QFileDialog, QAction, QMenu
from QuantStudio.Tools.QtGUI.Ui_IDSetup import Ui_IDSetupDlg

from QuantStudio.Tools.QtGUI.DateTimeSetup import mergeSet
from QuantStudio.FactorDataBase.FactorDB import FactorTable
from QuantStudio.Tools.FileFun import readCSV2Pandas
from QuantStudio.Tools.IDFun import suffixAShareID

class IDSetupDlg(QDialog, Ui_IDSetupDlg):
    """ID设置对话框"""
    def __init__(self, parent=None, ids=[], ft=None):
        super().__init__(parent)
        self.setupUi(self)
        self.IDs = ids.copy()
        self.CurInputID = ""
        self.isChanged = False
        # 设置因子库信息
        self.DateTimeEdit.setDateTime(dt.datetime.today())
        if isinstance(ft, FactorTable):
            self.FT = ft
            self.FDB = self.FT.FactorDB
            TableNames = (self.FDB.TableNames if self.FDB is not None else [self.FT.Name])
            self.FDBGroupBox.setTitle("来自: "+self.FDB.Name)
            self.FTComboBox.blockSignals(True)
            self.FTComboBox.addItems(TableNames)
            self.FTComboBox.setCurrentText(self.FT.Name)
            self.FTComboBox.blockSignals(False)
            self.FactorComboBox.addItems(self.FT.FactorNames)
        else:
            self.FDB = self.FT = None
            self.FDBGroupBox.setEnabled(False)
        # 初始化指数成分设置
        if not hasattr(self.FDB, "getID"): self.IndexGroupBox.setEnabled(False)
        self.DateEdit.setDate(dt.date.today())
        self.IndexIDEdit.setText("全体A股")
        self.populateIDListWidget(self.IDs)
        self.setIDListWidgetMenu()
    def showIDListWidgetMenu(self, pos):
        self.IDListWidget.ContextMenu["主菜单"].move(QCursor.pos())
        self.IDListWidget.ContextMenu["主菜单"].show()
    def setIDListWidgetMenu(self):
        # 设置 IDListWidget 的弹出菜单
        self.IDListWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.IDListWidget.customContextMenuRequested.connect(self.showIDListWidgetMenu)
        self.IDListWidget.ContextMenu = {"主菜单": QMenu(parent=self.IDListWidget)}
        self.IDListWidget.ContextMenu["主菜单"].addAction("删除选中项").triggered.connect(self.deleteIDListItems)
        self.IDListWidget.ContextMenu["主菜单"].addAction("清空").triggered.connect(self.clearIDList)
        self.IDListWidget.ContextMenu["导入导出"] = {"主菜单": QMenu("导入导出", parent=self.IDListWidget.ContextMenu["主菜单"])}
        self.IDListWidget.ContextMenu["导入导出"]["主菜单"].addAction("导入 ID").triggered.connect(self.importData)
        self.IDListWidget.ContextMenu["导入导出"]["主菜单"].addAction("导出 ID").triggered.connect(self.exportData)
        self.IDListWidget.ContextMenu["主菜单"].addMenu(self.IDListWidget.ContextMenu["导入导出"]["主菜单"])
        return 0
    def populateIDListWidget(self, ids):
        self.IDListWidget.clear()
        self.IDListWidget.addItems(ids)
        self.IDNumEdit.setText(str(len(ids)))
        return 0
    def deleteIDListItems(self):
        for iItem in self.IDListWidget.selectedItems():
            self.IDs.remove(iItem.text())
        return self.populateIDListWidget(self.IDs)
    def clearIDList(self):
        self.IDs = []
        self.IDListWidget.clear()
        self.IDNumEdit.setText("0")
        return 0
    @pyqtSlot()
    def on_AcceptButton_clicked(self):
        self.close()
        self.isChanged = True
        self.IDInputEdit.releaseKeyboard()
        return True
    @pyqtSlot()
    def on_RejectButton_clicked(self):
        self.close()
        self.IDInputEdit.releaseKeyboard()
        return False
    def exportData(self):
        if len(self.IDs)==0: return 0
        FilePath, _ = QFileDialog.getSaveFileName(None, "导出 ID", os.getcwd()+os.sep+"ID.csv", "csv (*.csv)")
        if not FilePath: return 0
        Data = pd.DataFrame(self.IDs, columns=["ID"])
        Data.to_csv(FilePath, header=False, index=False)
        return QMessageBox.information(None, "完成", "导出完成!")
    def importData(self):
        FilePath, _ = QFileDialog.getOpenFileName(None, "导入 ID", os.getcwd(), "csv (*.csv)")
        if not FilePath: return 0
        try:
            IDs = readCSV2Pandas(FilePath, detect_file_encoding=True, index_col=None, header=None)
        except Exception as e:
            return QMessageBox.critical(None, "错误", "数据读取失败: "+str(e))
        self.IDs = IDs.values[:, 0].tolist()
        return self.populateIDListWidget(self.IDs)
    @pyqtSlot()
    def on_IDInputEdit_returnPressed(self):
        ID = self.IDInputEdit.text()
        if not ID: return 0
        self.IDs = sorted(set(self.IDs).union({ID}))
        self.populateIDListWidget(self.IDs)
        self.IDInputEdit.setText('')
        self.CurInputID = ""
        return 0
    @pyqtSlot(str)
    def on_IDInputEdit_textEdited(self, p0):
        if p0.strip(self.CurInputID)==".": self.IDInputEdit.setText(suffixAShareID(p0[:-1]))
        self.CurInputID = p0
        return 0
    @pyqtSlot()
    def on_SelectIDButton_clicked(self):
        Date = self.DateEdit.date().toPyDate()
        IndexID = self.IndexIDEdit.text()
        isCurrent = (not self.CurrentCheckBox.isChecked())
        try:
            IDs = self.FDB.getID(index_id=IndexID, date=Date, is_current=isCurrent)
        except Exception as e:
            return QMessageBox.critical(None, "错误", "提取成分失败: "+str(e))
        if not IDs: return QMessageBox.warning(None, "警告", "提取的成分为空!\n可能的原因:\n(1)指数代码不正确;\n(2)该日期处无指数成分数据;\n(3)该指数因子库不支持.")
        self.IDs = sorted(mergeSet(set(IDs), set(self.IDs), merge_type=self.FIDSelectTypeComboBox.currentText()))
        return self.populateIDListWidget(self.IDs)
    @pyqtSlot()
    def on_SelectFDBIDButton_clicked(self):
        if self.IgnoreDTCheckBox.isChecked: TargetDT = None
        else: TargetDT = self.DateTimeEdit.dateTime().toPyDateTime()
        IDs = self.FT.getID(ifactor_name=self.FactorComboBox.currentText(), idt=TargetDT)
        self.IDs = sorted(mergeSet(set(IDs), set(self.IDs), merge_type=self.FIDSelectTypeComboBox.currentText()))
        return self.populateIDListWidget(self.IDs)
    @pyqtSlot(str)
    def on_FTComboBox_currentTextChanged(self, p0):
        self.FT = self.FDB.getTable(p0)
        self.FactorComboBox.clear()
        self.FactorComboBox.addItems(self.FT.FactorNames)

if __name__=="__main__":
    import QuantStudio.api as QS
    FDB = QS.FactorDB.WindDB2()
    FDB.connect()
    FT = FDB.getTable("中国A股日行情")
    from PyQt5.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    TestWindow = IDSetupDlg(None, ids=[], ft=FT)
    TestWindow.show()
    app.exec_()
    sys.exit()