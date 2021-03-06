"""This script transform a assembly graph generated by SPades,
convert it into a velvet's LastGraph. Note, the LastGraph generated
my not meet the full specification, it's only safe to be used in omacc package."""

import sys
import getopt
import fastg_file


def write_last_graph(nodes, output_file, overlap_size):
    with open(output_file, 'w') as fout:
        num_node = int(len(nodes) / 2)  # Eliminate reverse node.
        fout.write('\t'.join(map(str, (num_node, 0, overlap_size, 1)))) 
        fout.write('\n')
        nodes_item = list(nodes.items())
        nodes_item.sort(key=lambda x: int(x[0].rstrip('r')))
        # Write nodes.
        for i in range(0, len(nodes_item), 2):
            node_id, node_obj = nodes_item[i]
            node_id_reverse, node_obj_reverse = nodes_item[i + 1]
            if node_id.endswith('r'):
                node_id, node_id_reverse = node_id_reverse, node_id
                node_obj, node_obj_reverse = node_obj_reverse, node_obj
            num_kmer = int(node_obj.coverage * (node_obj.length - overlap_size))
            fout.write('\t'.join(['NODE', node_id, str(node_obj.length - overlap_size),
                str(num_kmer), str(num_kmer), '0', '0']))
            fout.write('\n')
            assert node_id_reverse.rstrip('r') == node_id
            fout.write(node_obj.seq[overlap_size:])
            fout.write('\n')
            fout.write(node_obj_reverse.seq[overlap_size:])
            fout.write('\n')
        # Write ARC
        arcs_writen = set()
        arc_multiplicity = 0  # Since this value is not ultilized, it's safe to set to 0.
        for node in tuple(zip(*nodes_item))[1]:
            for child_node, _ in node.children:
                if (node, child_node) not in arcs_writen:
                    node_ids = []
                    for n in (node, child_node):
                        if n.uid.endswith('r'):
                            node_ids.append('-' + n.uid[:-1])
                        else:
                            node_ids.append(n.uid)
                    fout.write('\t'.join(('ARC', *node_ids, str(arc_multiplicity))))
                    fout.write('\n')
                    arcs_writen.add((node, child_node))
                    arcs_writen.add((child_node, node))

def print_help():
    body = '-k OVERLAP_SIZE <fastg file> <output_file>'
    print("python3 {} {}".format(__file__, body))

def main():
    interface = 'hk:'
    options, args = getopt.getopt(sys.argv[1:], interface)
    overlap_size = None
    for option, value in options:
        if option == '-h':
            print_help()
            sys.exit()
        elif option == '-k':
            overlap_size = int(value)

    input_file, output_file = args
    nodes = fastg_file.build_assembly_graph(input_file, overlap_size)
    write_last_graph(nodes, output_file, overlap_size)
            

if __name__ == "__main__":
    main()