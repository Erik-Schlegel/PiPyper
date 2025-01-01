import typing
import multiprocessing
import threading
from pysndfx import AudioEffectsChain
from setproctitle import setproctitle
import prctl

import numpy
from track import Track


def add_track_fx(tracks: list[Track]) -> list[Track]:
    ## pool lets us more easily process multiple items simultaneously (each in its own process) and return when complete
    ## However, each processes creates a duplicate of it's parent's memory, and this leads to a big spike in resource usage.
    ## Even with my small program this pegs 4 processors, and uses %50 more memory while executing
    # with multiprocessing.Pool() as pool:
    #     results = pool.map(process_track_fx, tracks)

    # for track, processed_samples in zip(tracks, results):
    #     track.samples = processed_samples

    # return tracks


    # Threads are supposedly not as good for proc-intensive operations (don't know why yet), but they actually outperform processes
    # in this case (less mem use, less cpu use, faster app startup time)
    threads = []
    results = [None] * len(tracks)

    def process_track_wrapper(track, index):
        results[index] = process_track_fx(track)

    for index, track in enumerate(tracks):
        thread = threading.Thread(target=process_track_wrapper, args=(track, index))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    for track, processed_samples in zip(tracks, results):
        track.samples = processed_samples

    return tracks


def process_track_fx(track) -> numpy:
    prctl.set_name(f'fx:{track.track_name}')
    fx = AudioEffectsChain()
    samples = track.samples

    for eq in track.get_audio_option('equalizers'):
        fx = fx.equalizer(
            frequency=eq['frequency'],
            q=eq['slope'],
            db=eq['db']
        )
    samples = fx(samples.T).T

    reverb_conf = track.get_audio_option('reverb')
    mix = reverb_conf.pop('mix', 1)

    if reverb_conf.get('reverberance', 0) > 0 and mix > 0:
        fx = fx.reverb(**reverb_conf)
        wet_samples = fx(samples.T).T
        if wet_samples.shape != samples.shape:
            wet_samples = wet_samples.reshape(samples.shape)

        dry_amount = 1 - mix
        wet_amount = mix
        samples = (samples * dry_amount) + (wet_samples * wet_amount)

    samples = samples * track.get_audio_option('volume')
    return samples
