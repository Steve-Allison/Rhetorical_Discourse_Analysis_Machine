"""Offline UniRST corpus document conversion."""

import shutil
import sys
from pathlib import Path
from typing import Any, override

import numpy as np
from nltk import Tree

from . import common
from . import relation_set
from . import utils_dis_thiago
from . import utils_rs3
from .span_node import SpanNode as SpanNode

"""
TODO:
    - for now, read the entire corpus before writing, do both at the same time
    - still issues with the ps output (warning + not really pretty print)
"""


class Corpus:
    def __init__(self, tbpath: str | Path, datatype: str = "dis", mapping: bool = True, draw: bool = True) -> None:
        self.path = tbpath
        self.datatype = datatype
        self.draw = draw  # draw a ps file for each tree
        self.files: list[Path] = []
        self.edufiles: list[Path] = []
        self.documents: list[Document] = []
        self.validDocuments: list[Document] = []  # document for which a valid tree has been built
        self.outputExt = ".dmrg"  # Extension of the output tree files
        self.mapping = mapping
        # Keep track of the original/final relation set
        self.originLabels: set[tuple[str, str]] = set()
        self.finalLabels: set[tuple[str, str]] = set()
        self.pb_files: list[str] = []

    def read(self) -> None:
        self.getDocuments()
        for doc in self.documents:
            print("Reading:", Path(doc.path).name, file=sys.stderr)
            doc.read()
            common.addLabels(doc.tree, self.originLabels)
            if self.mapping:
                doc.mapRelation("mapping")
            common.addLabels(doc.tree, self.finalLabels)
        self.validDocuments = [d for d in self.documents if d.tree is not None]
        # self.validDocuments = self.documents
        self.pb_files = [str(d.path) for d in self.documents if d.tree is None]
        print("\t#Files read:", len(self.files), "#Tree built:", len(self.validDocuments), file=sys.stderr)

    def write(self, outpath: str | Path) -> None:
        out = Path(outpath)
        out.mkdir(exist_ok=True)
        for doc in self.validDocuments:
            print("Writing:", Path(doc.path).name, file=sys.stderr)
            doc.writeTree(out, self.outputExt)
            doc.writeEdu(out)
            if self.draw:  # create a picture representing the tree
                ext = f".{doc.datatype}" if doc.datatype else ""
                doc.drawTree(out, ext, ".ps")
        # Write the list of documents for which we couldn't build a tree
        if len(self.pb_files) != 0:
            (out / "pb_files").write_text("\n".join(self.pb_files), encoding="utf-8")

    def getDocuments(self) -> None:
        if self.datatype == "dis":
            # retrieve tree files DisDocument(
            self.files = getFiles(self.path, ".dis")
            # retrieve edu files
            self.edufiles = getFiles(self.path, ".edus")
            # Associate each tree with the corresponding edu file
            self.documents = []
            self.documents.extend(associate_tree_edus(self.files, self.edufiles))
        elif self.datatype == "rs3":
            self.files = getFiles(self.path, ".rs3")
            self.documents = [Rs3Document(f) for f in self.files]
        elif self.datatype == "thiago":
            self.files = getFiles(self.path, ".txt.lisp.thiago")
            self.documents = [ThiagoDocument(f) for f in self.files]
        else:
            raise SystemExit("Unknown data type " + self.datatype)

    def printLabels(self) -> None:
        """The label sets record tuples (relation, nuclearity)"""
        # -- Originaly
        labels = np.unique([l for (l, n) in self.originLabels])
        print("\n#Original Labels:" + str(len(labels)))
        print(", ".join(sorted(labels)))
        # -- Finaly/mapped
        labels = np.unique([l for (l, n) in self.finalLabels])
        print("\n#Final Labels:" + str(len(labels)))
        print(", ".join(sorted(labels)))

    def __str__(self) -> str:
        return " ".join([str(self.path), "Type:", self.datatype])


# ----------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------
class Document:
    def __init__(self, dpath: str | Path) -> None:  # ? parse=parse, raw=raw
        self.path = str(dpath)
        self.datatype: str | None = None
        self.tree: Tree | None = None
        self.tokendict: Any = None  # Token dict: id token in the document -> token form
        self.eduIds: list[int] = []
        self.edudict: Any = None  # EDU dict: id EDU -> list of id tokens
        self.outbasename = Path(self.path).name  # Name of the output file, can be modified for the RST DT
        self.statistics: dict[str, object] = {}  # statistics for one document

    def read(self) -> None:
        raise NotImplementedError

    def writeTree(self, outpath: str | Path, outExt: str) -> None:
        """
        Write the bracketed tree into a file
        Remove the original extension, keep only .outExt as extension
        """
        stem = self.outbasename.replace(".out", "").replace(".txt.lisp", "")
        if self.datatype:
            stem = stem.replace("." + self.datatype, "")
        fileout = Path(outpath) / f"{stem}{outExt}"
        fileout.write_text(self.tree.__str__().strip(), encoding="utf-8")

    def drawTree(self, outpath: str | Path, ext: str, outExt: str, docno: int = -1) -> None:
        """Draw RST tree into a file"""
        pass

    def writeEdu(self, outpath: str | Path) -> None:
        raise NotImplementedError

    def mapRelation(self, mappingRel: str) -> None:
        if self.tree is None:
            return
        if Path(mappingRel).is_file():
            raise SystemExit("Mapping RS3 from file not implemented yet")
        else:
            if mappingRel == "mapping":  # Default general mapping
                common.performMapping(self.tree, relation_set.mapping)
            elif mappingRel == "basque_labels":
                common.performMapping(self.tree, relation_set.basque_labels)
            elif mappingRel == "brazilianCst_labels":
                common.performMapping(self.tree, relation_set.brazilianCst_labels)
            elif mappingRel == "brazilianSum_labels":
                common.performMapping(self.tree, relation_set.brazilianSum_labels)
            elif mappingRel == "germanPcc_labels":
                common.performMapping(self.tree, relation_set.germanPcc_labels)
            elif mappingRel == "spanish_labels":
                common.performMapping(self.tree, relation_set.spanish_labels)
            elif mappingRel == "rstdt_mapping18":
                common.performMapping(self.tree, relation_set.rstdt_mapping18)
            elif mappingRel == "dutch_labels":
                common.performMapping(self.tree, relation_set.dutch_labels)
            elif mappingRel == "brazilianTCC_labels":
                common.performMapping(self.tree, relation_set.brazilianTCC_labels)
            else:
                print("Unknown mapping: " + mappingRel)


class Rs3Document(Document):
    """
    Class for a document encoded in rs3 format.
    - XML format
    - the relation list in the header gives the nuclearity of the relations
    - EDU id are not always continuous: EDU are renamed
    - For some corpora/languages, the binarization using right branching is not enough,
    a more general strategy is used
    - An EDU file is created
    """

    def __init__(self, dpath: str | Path) -> None:
        Document.__init__(self, dpath)
        self.datatype = "rs3"
        self.nuclearity_relations = {}

    @override
    def read(self) -> None:
        """
        Create a binarized (NLTK) Tree, self.tree, from the rs3 file
        Fill self.tokendict and self.edudict
        """
        doc_root, rs3_xml_tree = utils_rs3.parseXML(self.path)
        if doc_root is None or rs3_xml_tree is None:
            raise ValueError(f"RS3 document could not be parsed: {self.path}")
        # Retrieve the relations in the header (used to find multinuc rel)
        self.nuclearity_relations = utils_rs3.getRelationsType(rs3_xml_tree)
        # Get info for each node
        eduList, groupList, root = utils_rs3.readRS3Annotation(doc_root)
        if root is None:
            raise ValueError(f"RS3 document has no resolvable root: {self.path}")
        # Build nodes, rename DU, tree=SpanNode instance
        tree = utils_rs3.buildNodes(eduList, groupList, root, self.nuclearity_relations)
        # Can t be retrieved from the tree for now, some EDU have children
        eduIds: list[int] = []
        for edu in eduList:
            edu_id = edu.get("id")
            if not isinstance(edu_id, int):
                raise ValueError(f"RS3 EDU has a non-integer ID: {edu_id!r}")
            eduIds.append(edu_id)
        # Order span list for each node
        utils_rs3.orderSpanList(tree, eduIds)
        # Clean the tree: deal with DU with only one child + same unit cases
        utils_rs3.cleanTree(tree, eduIds, self.nuclearity_relations, self)
        # Retrieve info about the text of the EDUs
        self.tokendict, self.edudict = utils_rs3.retrieveEdu(tree, eduIds)
        # non_bin_tree = tree
        # Binarize the tree
        utils_rs3.binarizeTreeGeneral(tree, self, nucRelations=self.nuclearity_relations)
        tree = common.backprop(tree, self)  # Backprop info
        self.tree = Tree.fromstring(common.parse(tree))  # Build an nltk tree
        if self.tree is None:
            raise ValueError(f"RS3 parser produced no NLTK tree: {self.path}")
        validTree = common.checkTree(self.tree, self)
        if not validTree:
            self.tree = None

    def writeEdu(self, outpath: str | Path) -> None:
        utils_rs3.writeEdus(self, ".rs3", outpath)


# ----------------------------------------------------------------------------------
class DisDocument(Document):
    def __init__(self, dpath: str | Path, epath: str | Path) -> None:
        Document.__init__(self, dpath)
        self.datatype = "dis"
        self.eduPath = epath

    @override
    def read(self) -> None:  # , eduFiles
        basename = Path(self.path).name
        for e in [".out", ".dis", ".txt", ".edus"]:
            basename = basename.replace(e, "")
        if basename in utils_dis_thiago.file_mapping:  # Modify the name of some specific files in the RST DT
            self.outbasename = utils_dis_thiago.file_mapping[basename]
        tree, self.eduIds = utils_dis_thiago.buildTree(Path(self.path).read_text(encoding="utf-8"))  # Build RST Tree
        tree = utils_dis_thiago.binarizeTreeRight(tree)  # Binarize it
        # doc = utils_dis_thiago.readEduDoc(self.eduPath, self)  # Retrieve info on EDUs
        tree = common.backprop(tree, self)
        str_tree = common.parse(tree)  # Get nltk tree
        self.tree = Tree.fromstring(str_tree)

    def writeEdu(self, outpath: str | Path) -> None:
        # copy the EDU file, possibly rename it using the file mapping
        if self.outbasename != Path(self.path.split(".")[0]).name:
            shutil.copy(
                self.eduPath,
                Path(outpath) / (self.outbasename.replace(".out", "").replace(".dis", "") + ".edus"),
            )
        else:
            shutil.copy(str(self.eduPath).replace(".out", "").replace(".dis", ""), outpath)


# ----------------------------------------------------------------------------------
class ThiagoDocument(Document):
    def __init__(self, dpath: str | Path) -> None:
        Document.__init__(self, dpath)
        self.datatype = "thiago"
        self.eduPath = None

    @override
    def read(self) -> None:
        tree, self.eduIds, allnodes, self.edudict = utils_dis_thiago.buildTreeThiago(
            Path(self.path).read_text(encoding="windows-1252")
        )
        tree = utils_dis_thiago.bTree(allnodes, self.path)
        tree = utils_dis_thiago.binarizeTreeRightThiago(tree)
        tree = common.backprop(tree, self)  # Backprop info
        self.tree = Tree.fromstring(common.parse(tree))

    def writeEdu(self, outpath: str | Path) -> None:
        common.writeEdusFile(self, ".txt.lisp.thiago", outpath)


# ----------------------------------------------------------------------------------
def associate_tree_edus(treeFiles: list[Path], eduFiles: list[Path]) -> list[DisDocument]:
    """Retrieve the EDU file associated to a tree for the dis format"""
    documents = []
    for treePath in treeFiles:
        basename = Path(treePath).name
        for e in [".out", ".dis", ".txt", ".edus"]:
            basename = basename.replace(e, "")
        eduPath = utils_dis_thiago.findFile(eduFiles, basename)  # Retrieve EDUs file
        if eduPath is None:
            raise SystemExit("Edus file not found: " + basename)
        documents.append(DisDocument(treePath, eduPath))
    return documents


def getFiles(tbpath: str | Path, ext: str) -> list[Path]:
    files: list[Path] = []
    root = Path(tbpath)
    for dirpath, dirnames, filenames in root.walk():
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for file in filenames:
            if not file.startswith(".") and file.endswith(ext):
                files.append(dirpath / file)
    return files
