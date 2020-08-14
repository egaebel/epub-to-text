import argparse
import epub
import html2text
import inspect
import os
import re
import sys

CHAPTERS = "chapters"

def epub_to_txt(
        epub_file_name,
        file_dir="epub-files",
        output_file_dir="txt-files",
        chapter_files_dir=None,
        debug=False,
        dry_run=False):
    if chapter_files_dir is None:
        chapter_files_dir = os.path.join(output_file_dir, CHAPTERS)
    _try_mkdirs(output_file_dir)
    _try_mkdirs(chapter_files_dir)

    html_to_text = html2text.HTML2Text()
    html_to_text.ignore_links = True

    # Ignore hidden files
    if epub_file_name[0] == '.':
        return
    # Ignore files that don't have the epub extension
    if os.path.splitext(epub_file_name)[1] != ".epub":
        return

    print("Opening file: %s" % epub_file_name)
    ebook = epub.open_epub(os.path.join(file_dir, epub_file_name))
    book_title = ebook.toc.title
    print("Starting on book: %s" % book_title)

    # Works with Expanse, old code
    """
    play_order = [nav_point.play_order for nav_point in ebook.toc.nav_map.nav_point]
    play_order_labels = [str(nav_point.play_order) for nav_point in ebook.toc.nav_map.nav_point]
    labels = [nav_point.labels[0][0] for nav_point in ebook.toc.nav_map.nav_point]
    source_references = [nav_point.src for nav_point in ebook.toc.nav_map.nav_point]
    """

    play_order = list()
    play_order_labels = list()
    labels = list()
    source_references = list()

    def get_all_nav_points(nav_point):
        if len(nav_point.nav_point) == 0:
            return [nav_point]
        else:
            nav_points_list = [nav_point]
            for sub_nav_point in nav_point.nav_point:
                nav_points_list += get_all_nav_points(sub_nav_point)
            return nav_points_list

    for nav_point_root in ebook.toc.nav_map.nav_point:
        for nav_point in get_all_nav_points(nav_point_root):
            play_order.append(nav_point.play_order)
            play_order_labels.append(str(nav_point.play_order))
            labels.append(nav_point.labels[0][0])
            source_references.append(nav_point.src)


    #"""
    play_order_label_to_index = dict([(x[0], index) for index, x in enumerate(ebook.opf.spine.itemrefs)])

    play_order_labels = [x[0] for x in ebook.opf.spine.itemrefs]
    play_order = [str(i) for i in range(len(ebook.opf.spine.itemrefs))]
    labels = sorted(
        list(
            filter(
                lambda x: x in play_order_label_to_index,
                ebook.opf.manifest.keys())),
        key=lambda x: play_order_label_to_index[x])
    source_references = list(
        map(
            lambda x: x[1],
            sorted(
                list(filter(lambda x: x[0] in play_order_label_to_index, ebook.opf.manifest.items())),
                key=lambda x: play_order_label_to_index[x[0]])))
    #"""

    if debug:
        print("play_order:\n'%s'\n\n" % str(play_order))
        print("play_order_labels:\n'%s'\n\n" % str(play_order_labels))
        # print("play_order_label_to_index dict:\n'%s'\n\n" % str(play_order_label_to_index))
        print("labels:\n'%s'\n\n" % str(labels))
        print("source_references:\n'%s'\n\n" % str(source_references))

    assert len(labels) == len(source_references) and len(labels) == len(play_order_labels), (
        "Not true that: len(labels): '%d' == len(source_references): '%d' and len(labels): '%d' == len(play_order_labels): '%d'"
        % (len(labels), len(source_references), len(labels), len(play_order_labels)))

    chapter_label_source_tuples = list(zip(play_order, play_order_labels, labels, source_references))
    if debug:
        print("chapter_label_source_tuples:\n%s\n\n" % "\n".join(list(map(lambda x: str(x), chapter_label_source_tuples))))

    full_book_content = list()
    for chapter_order, chapter_order_label, chapter_title, source_ref in chapter_label_source_tuples:
        chapter_info_string = "Book: %s Chapter: %s titled: %s"\
            % (book_title, chapter_order, chapter_title)
        try:
            chapter_content = ebook.read_item(source_ref)
            if debug:
                print("chapter_order: '%s', chapter_order_label: '%s', chapter_title: '%s', source_ref: '%s', read source_ref:\n'%s'\n\n"
                    % (
                        chapter_order,
                        str(chapter_order_label),
                        str(chapter_title),
                        str(source_ref),
                        str(ebook.read_item(source_ref)[:min(20, len(ebook.read_item(source_ref)))])))
        except Exception as e:
            print("Exception: e: '%s'" % str(e))
            if isinstance(e, KeyError):
                print("KeyError: e: '%s'" % str(e))
                sys.stdout.flush()
                if ".jpg" in str(e):
                    continue
                else:
                    raise e

            print("Failed getting chapter: %s %s in book %s, exception: %s"
                % (chapter_order, chapter_title, ebook.toc.title, str(e)))
            ref_fixed = re.sub("#.*", "", source_ref)
            try:
                chapter_content = ebook.read_item(ref_fixed)
                print("Success on retry! %s" % chapter_info_string)
            except:
                print("FAILED ON RETRY TOO for book titled: %s with ref: %s."
                    % (book_title, ref_fixed))
        try:
            string_chapter_content = chapter_content.decode("utf-8")
        except UnicodeDecodeError as e:
            print("TypeError while decoding content with UTF-8 on chapter titled: '%s'" % chapter_title)
            continue
        chapter_content = html_to_text.handle(str(string_chapter_content))
        full_book_content.append((chapter_order, chapter_title, chapter_content))
    with open(os.path.join(output_file_dir, os.path.splitext(epub_file_name)[0] + ".txt"), "w") as txt_file:
        for chapter_index, chapter_tuple in enumerate(full_book_content):
            order = chapter_tuple[0]
            if order.strip() == "":
                order = str(chapter_index)
            title = chapter_tuple[1]
            content = chapter_tuple[2]

            if not dry_run:
                txt_file.write(content)

            chapter_file_name = epub_file_name.replace(".epub", "")
            chapter_file_name += "--" + order.zfill(5) + "--" + title
            chapter_file_name += ".txt"
            if not dry_run:
                with open(os.path.join(chapter_files_dir, chapter_file_name), "w") as chapter_txt_file:
                    chapter_txt_file.write(content)

    ebook.close()

def _try_mkdirs(dir_name):
    try:
        os.makedirs(dir_name)
    except Exception as e:
        print("Failed to mkdirs: %s" % str(e))
        pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--epub-file-path", default=None)
    parser.add_argument("-o", "--output-dir", default=".")
    parser.add_argument("-c", "--output-chapter-dir", default=None)
    parser.add_argument("-d", "--debug", action="store_true")
    parser.add_argument("-r", "--dry-run", action="store_true")
    args = parser.parse_args()

    if args.epub_file_path is None:
        print("Must provide an epub file!")
        sys.exit(1)

    epub_to_txt(
        os.path.basename(args.epub_file_path),
        file_dir=os.path.dirname(args.epub_file_path),
        output_file_dir=args.output_dir,
        chapter_files_dir=args.output_chapter_dir,
        debug=args.debug,
        dry_run=args.dry_run)
    print("Done!")
