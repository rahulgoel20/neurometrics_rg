import logging
import numpy
import pickle
import datetime
import h5py
from os import path
from mvpa2.misc.io import ColumnData
from mvpa2.datasets import dataset_wizard
from mvpa2.datasets.mri import fmri_dataset
from sklearn.feature_selection import SelectKBest
from sklearn.pipeline import Pipeline
from sklearn.svm import SVC
from sklearn.cross_validation import LeaveOneLabelOut
from sklearn.cross_validation import cross_val_score
from sklearn.cross_validation import permutation_test_score
from sklearn.metrics import classification_report
from sklearn.metrics import accuracy_score
from sklearn.grid_search import GridSearchCV
from neurometrics.neural_network import FeedForwardNeuralNetwork

block_size = 18 #FIXME: figure out how to git rid of this

def vote(votes, classes=None, weights=None):
    if weights is None:
        weights = numpy.ones(votes.shape)
    if classes is None:
        classes = set(votes)
    return classes[numpy.argmax([weights[votes==c].sum() for c in classes])]

def block_vote_score(y_true, y_pred, block_size):
    classes = set(y_true)
    vote_true = [vote(v,classes) for v in y_true.reshape(-1,block_size)]
    vote_pred = [vote(v,classes) for v in y_pred.reshape(-1,block_size)]
    return accuracy_score(vote_true, vote_pred)

def block_probability_score(y_true, y_pred, y_proba, block_size):
    classes = set(y_true)
    vote_true = [vote(v,classes) for v in y_true.reshape(-1,block_size)]
    c = y_proba.reshape(len(classes),-1,block_size)
    vote_pred = numpy.argmax(c.sum(axis=2),axis=0)
    return accuracy_score(vote_true, vote_pred)

def score(clf, X, y):
    return {'report':classification_report(y,clf.predict(X)),
            'accuracy':accuracy_score(y,clf.predict(X)),
            'block_vote':block_vote_score(y,clf.predict(X),block_size),
            'block_proba':block_probability_score(y,clf.predict(X),clf.predict_proba(X),block_size),
            'y':y,
            'predict':clf.predict(X),
            'predict_proba':clf.predict_proba(X)}

def cross_val(clf, X, y, cv, scoring):
    return [scoring(clf.fit(X[train],y[train]),X[test],y[test]) for train,test in cv]

def do_session(attr_file='attributes.txt',
               nifti_file='mri/f.nii.gz',
               clf=None,
               scoring=score,
               n_jobs = 1,
               permutation_test = False):

    logger = logging.getLogger(__name__)

    logger.info(session_dir)

    logger.info('Loading attributes: {0}'.format(attr_file))
    attr = ColumnData(attr_file)

    logger.info('Loading fmri dataset: {0}'.format(nifti_file))
    ds = fmri_dataset(samples = nifti_file,
                      targets = attr.quantized_distance,
                      chunks = attr.run)

    for k in attr.keys():
        ds.sa[k] = attr[k]

    #fixme: do wiener filter here

    from mvpa2.mappers.detrend import PolyDetrendMapper

    detrender = PolyDetrendMapper(polyord = 1, chunks_attr='chunks')

    ds = ds.get_mapped(detrender)

    ds = ds[numpy.logical_not(numpy.logical_or(ds.sa.move, ds.sa.cue)), :]

    fs = SelectKBest(k=3000)

    fs.fit(ds.samples, ds.sa.search > 0)

    ds = ds[ds.sa.search > 0, :]

    ds = ds[:, fs.get_support()]

    logger.info('Configuring cross validation')
    cv = LeaveOneLabelOut(ds.chunks)

    if clf is None:
        clf = SVC(kernel='linear',probability=True)

    logger.info('Beginning cross validation')
    scores = cross_val(clf,
                       ds.samples,
                       ds.targets,
                       cv,
                       scoring)

    if permutation_test:
        logger.info('Beginning permutation test')
        score, 
        permutation_scores, 
        pvalue = permutation_test_score(clf,
                                        ds.samples,
                                        ds.targets,
                                        cv = cv,
                                        n_jobs = n_jobs,
                                        verbose = 50,
                                        scoring = 'accuracy')
        
    result = {}
    result['datetime'] = datetime.datetime.now()
    result['attr_file'] = attr_file
    result['nifti_file'] = nifti_file
    result['fs'] = fs
    result['mapper'] = ds.mapper
    result['clf'] = clf
    result['scoring'] = scoring
    result['scores'] = scores
    if permutation_test:
        result['pvalue'] = pvalue;
    else:
        result['pvalue'] = None

    return result
       
#logging.basicConfig(level=logging.INFO)

#logger = logging.getLogger(__name__)

#sessions = ['S010614af',
#            'S010614drB',
#            'S040414drB',
#            'S040414jkA',
#	    'S042814vs',
#            'S050214af']
        
#logger.info('Configuring classifier')
#fs = SelectKBest(k = 3000)
#svc = SVC(kernel='linear')
#nn = FeedForwardNeuralNetwork()
#clf = Pipeline([('ANOVA',fs),('Classifier',svc)])               

#results = [do_session(session,clf=svc) for session in sessions]



 

